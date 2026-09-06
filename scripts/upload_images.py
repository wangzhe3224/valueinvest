#!/usr/bin/env python3
"""上传报告图片到图床（SM.MS / 阿里云 OSS 双后端），并把 md 里的相对路径改写为公网 URL。

用法:
    source valueinvest/.venv/bin/activate
    python valueinvest/scripts/upload_images.py <report.md> --dry-run   # 预览将上传的图片
    python valueinvest/scripts/upload_images.py <report.md>             # 上传并原地改写 md
    python valueinvest/scripts/upload_images.py <folder>                # 只上传文件夹内全部图片
    python valueinvest/scripts/upload_images.py <report.md> --backend oss

后端配置（二选一，或 ~/.imagehost.json 里 "backend" 指定，--backend 可覆盖）:

1) SM.MS: token 存于 SMMS_TOKEN 环境变量 / ~/.smms_token / ~/.imagehost.json 的 smms_token
      注册 https://sm.ms → https://sm.ms/home/apitoken 生成

2) 阿里云 OSS: ~/.imagehost.json
      {
        "backend": "oss",
        "oss": {
          "access_key_id": "LTAI...",                // RAM 子账号的 AK，勿用主账号
          "access_key_secret": "...",
          "endpoint": "oss-cn-hangzhou.aliyuncs.com", // bucket 所在地域
          "bucket": "your-imgbed",
          "prefix": "valueinvest/",                    // 可选，key 前缀
          "custom_domain": "https://img.example.com"   // 可选，绑定的加速域名
        }
      }
   环境变量可覆盖: OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / OSS_ENDPOINT / OSS_BUCKET

行为:
    - 扫描 md 中所有相对路径的图片引用 ![](...)
    - 逐张上传；md 中 `](相对路径)` 原地改写为公网 URL；本地图片原样保留（备份）
    - 上传映射存到 /tmp/<md名>_imgbed_map.json

发布到知乎: md 改写后粘贴到 mdnice.com / doocs-md → "复制到知乎" → 知乎编辑器粘贴，
知乎会把外链图自动转存到 zhimg.com。
"""

import argparse
import datetime
import json
import mimetypes
import os
import re
import sys
import time
from urllib.parse import quote

import requests  # sm.ms 会 308 跳转到 s.ee，requests 自动跟随

SMMS_API = "https://sm.ms/api/v2/upload"
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")


# ---------------------------------------------------------------- 配置
def load_config() -> dict:
    p = os.path.expanduser("~/.imagehost.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f) or {}
    return {}


def load_smms_token(cfg: dict):
    tok = os.environ.get("SMMS_TOKEN", "").strip()
    if tok:
        return tok
    p = os.path.expanduser("~/.smms_token")
    if os.path.exists(p):
        return open(p).read().strip()
    return cfg.get("smms_token")


def load_oss_cfg(cfg: dict) -> dict | None:
    c = dict(cfg.get("oss") or {})
    c["access_key_id"] = os.environ.get("OSS_ACCESS_KEY_ID", c.get("access_key_id"))
    c["access_key_secret"] = os.environ.get("OSS_ACCESS_KEY_SECRET", c.get("access_key_secret"))
    c["endpoint"] = os.environ.get("OSS_ENDPOINT", c.get("endpoint"))
    c["bucket"] = os.environ.get("OSS_BUCKET", c.get("bucket"))
    if all(c.get(k) for k in ("access_key_id", "access_key_secret", "endpoint", "bucket")):
        return c
    return None


def resolve_backend(args, cfg: dict):
    """返回 (backend_name, backend_param)。优先级: --backend > 配置 backend > 自动探测。"""
    want = args.backend
    if not want:
        want = cfg.get("backend")
    if not want:  # 自动探测
        if load_oss_cfg(cfg):
            want = "oss"
        elif load_smms_token(cfg):
            want = "smms"
    if want == "oss":
        oss = load_oss_cfg(cfg)
        if not oss:
            sys.exit("[upload_images] 未找到完整的 OSS 配置：请在 ~/.imagehost.json 配置 oss 段"
                     "（access_key_id/secret/endpoint/bucket），或设置 OSS_* 环境变量")
        return "oss", oss
    if want == "smms":
        tok = load_smms_token(cfg)
        if not tok:
            sys.exit("[upload_images] 缺少 SM.MS token（sm.ms 已迁移 s.ee，强制鉴权）。\n"
                     "  1. 注册/登录 https://sm.ms → https://sm.ms/home/apitoken 生成 token\n"
                     "  2. 写入:  echo '<token>' > ~/.smms_token && chmod 600 ~/.smms_token\n"
                     "     或:    export SMMS_TOKEN=<token>\n"
                     "  或改用 OSS 后端: --backend oss")
        return "smms", tok
    sys.exit(f"[upload_images] 未知后端: {want}（支持 oss / smms）")


# ---------------------------------------------------------------- 上传实现
def _find_url(obj, depth=0):
    """防御性解析: 在 sm.ms 响应 JSON 里找第一个像图片 URL 的字符串（兼容 sm.ms v2 / s.ee v1）。"""
    if depth > 6:
        return None
    if isinstance(obj, str):
        if obj.startswith(("http://", "https://")) and (
                "/image/" in obj or "i.loli.net" in obj or "s.ee/i" in obj
                or obj.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))):
            return obj
        return None
    if isinstance(obj, dict):
        for k in ("url", "smurl", "images", "link", "path"):
            if k in obj:
                u = _find_url(obj[k], depth + 1)
                if u:
                    return u
    if isinstance(obj, list):
        for v in obj:
            u = _find_url(v, depth + 1)
            if u:
                return u
    return _find_url(list(obj.values()), depth + 1) if isinstance(obj, dict) else None


def put_smms(path: str, token: str) -> str:
    fname = os.path.basename(path)
    mime = mimetypes.guess_type(fname)[0] or "image/png"
    with open(path, "rb") as f:
        r = requests.post(SMMS_API, files={"smfile": (fname, f, mime)},
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=60, allow_redirects=True)
    js = r.json()
    url = _find_url(js)
    if not url:
        raise RuntimeError(js.get("message") or json.dumps(js, ensure_ascii=False)[:200])
    return url


def put_oss(path: str, cfg: dict) -> str:
    try:
        import oss2  # uv pip install oss2
    except ImportError:
        sys.exit("[upload_images] OSS 后端需要 SDK：uv pip install oss2")
    fname = os.path.basename(path)
    mime = mimetypes.guess_type(fname)[0] or "image/png"
    auth = oss2.Auth(cfg["access_key_id"], cfg["access_key_secret"])
    bucket = oss2.Bucket(auth, f"https://{cfg['endpoint']}", cfg["bucket"])
    prefix = cfg.get("prefix", "")
    key = f"{prefix}{datetime.date.today():%Y%m%d}/{fname}"
    with open(path, "rb") as f:
        bucket.put_object(key, f, headers={"ContentType": mime})
    base = (cfg.get("custom_domain") or f"https://{cfg['bucket']}.{cfg['endpoint']}").rstrip("/")
    return f"{base}/{quote(key)}"


def upload(path: str, backend: str, param, retries: int = 2) -> str:
    put = put_oss if backend == "oss" else put_smms
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return put(path, param)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 - 统一重试
            last_err = e
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"{os.path.basename(path)}: {last_err}")


# ---------------------------------------------------------------- 扫描与改写
def collect_refs(md_path: str, exts) -> list:
    """md 中相对路径且真实存在的图片引用（相对 md 所在目录解析）。"""
    base = os.path.dirname(os.path.abspath(md_path))
    text = open(md_path, encoding="utf-8").read()
    refs, seen = [], set()
    for m in IMG_RE.finditer(text):
        rel = m.group(1).strip('"\'<>')
        if rel.startswith(("http://", "https://", "data:")):
            continue
        if os.path.splitext(rel)[1].lower().lstrip(".") not in exts:
            continue
        abs_path = os.path.normpath(os.path.join(base, rel))
        if abs_path in seen or not os.path.isfile(abs_path):
            continue
        seen.add(abs_path)
        refs.append((rel, abs_path))
    return refs, text


def main():
    ap = argparse.ArgumentParser(description="上传图片到图床（smms/oss）并改写 md 引用")
    ap.add_argument("target", help="报告 .md 文件 或 图片文件夹")
    ap.add_argument("--dry-run", action="store_true", help="只列出将上传的图片，不实际上传/改写")
    ap.add_argument("--ext", default="png,jpg,jpeg,webp", help="图片扩展名（默认 png,jpg,jpeg,webp）")
    ap.add_argument("--backend", choices=["oss", "smms"], default=None, help="图床后端（默认读配置/自动探测）")
    args = ap.parse_args()
    exts = {e.strip(".").lower() for e in args.ext.split(",")}
    cfg = load_config()

    def backend_or_none():
        try:
            return resolve_backend(args, cfg)
        except SystemExit:
            return "(未配置)", None

    # --- 模式 A: 文件夹（只上传不改写）
    if os.path.isdir(args.target):
        files = sorted(os.path.join(args.target, f) for f in os.listdir(args.target)
                       if os.path.splitext(f)[1].lower().lstrip(".") in exts)
        if args.dry_run:
            print(f"[upload_images] dry-run（后端 {backend_or_none()[0]}）：文件夹内 {len(files)} 张图")
            for f in files:
                print(f"  {os.path.basename(f)}  ({os.path.getsize(f)/1024:.0f} KB)")
            return
        backend, param = resolve_backend(args, cfg)
        rows = []
        for f in files:
            url = upload(f, backend, param)
            rows.append((f, url))
            print(f"  {os.path.basename(f)} -> {url}", flush=True)
            time.sleep(1)
        _report(rows, None, backend=backend)
        return

    # --- 模式 B: md（上传 + 原地改写）
    md_path = args.target
    if not os.path.isfile(md_path):
        sys.exit(f"[upload_images] 文件不存在: {md_path}")
    refs, text = collect_refs(md_path, exts)
    if not refs:
        print("[upload_images] 没有需要上传的本地图片引用（可能已是公网 URL）")
        return
    if args.dry_run:
        bk, _ = backend_or_none()
        print(f"[upload_images] dry-run（后端 {bk}）：将上传 {len(refs)} 张图（md: {md_path}）")
        for rel, abs_path in refs:
            print(f"  {rel}  ({os.path.getsize(abs_path)/1024:.0f} KB)")
        return

    backend, param = resolve_backend(args, cfg)
    mapping, rows = {}, []
    for rel, abs_path in refs:
        url = upload(abs_path, backend, param)
        mapping[rel] = url
        rows.append((rel, url))
        print(f"  {rel} -> {url}", flush=True)
        time.sleep(1)  # 温和限速
        text = text.replace(f"]({rel})", f"]({url})")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(text)
    _report(rows, mapping, md_path, backend)


def _report(rows, mapping, md_path=None, backend="smms"):
    print(f"\n[upload_images] 完成 {len(rows)} 张（后端 {backend}）：")
    for src, url in rows:
        print(f"  {src} -> {url}")
    if mapping:
        map_file = f"/tmp/{os.path.splitext(os.path.basename(md_path))[0]}_imgbed_map.json"
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=1)
        print(f"[upload_images] 映射已存 {map_file}（本地原图保留作备份）")
    print("[upload_images] 发布知乎：把改写后的 md 粘贴到 mdnice.com / doocs-md → 复制到知乎 → 知乎编辑器粘贴")


if __name__ == "__main__":
    main()
