"""
Report generation utilities.
"""
from typing import List
from ..valuation.base import ValuationResult


def format_report(results: List[ValuationResult], title: str = "Valuation Report") -> str:
    lines = []
    lines.append("")
    lines.append("╔" + "═" * 68 + "╗")
    lines.append("║" + f" {title} ".center(68) + "║")
    lines.append("╚" + "═" * 68 + "╝")
    
    valid_results = [r for r in results if r.fair_value > 0]
    current_price = results[0].current_price if results else 0
    
    lines.append("")
    lines.append("┌" + "─" * 68 + "┐")
    lines.append("│ VALUATION SUMMARY".ljust(69) + "│")
    lines.append("├" + "─" * 68 + "┤")
    lines.append(f"│ {'Method':<30} {'Fair Value':>12} {'Margin':>12} {'Assessment':>12} │")
    lines.append("├" + "─" * 68 + "┤")
    
    for r in results:
        if r.fair_value > 0:
            margin_str = f"{r.premium_discount:+.1f}%"
        else:
            margin_str = "N/A"
        
        fair_str = f"${r.fair_value:.2f}" if r.fair_value > 0 else "N/A"
        
        lines.append(f"│ {r.method:<30} {fair_str:>12} {margin_str:>12} {r.assessment:>12} │")
    
    if valid_results:
        avg_val = sum(r.fair_value for r in valid_results) / len(valid_results)
        avg_margin = ((avg_val - current_price) / current_price) * 100
        lines.append("├" + "─" * 68 + "┤")
        lines.append(f"│ {'AVERAGE':<30} ${avg_val:>11.2f} {avg_margin:>+11.1f}% {'':>12} │")
    
    lines.append("├" + "─" * 68 + "┤")
    lines.append(f"│ {'CURRENT PRICE':<30} ${current_price:>11.2f} {'--':>12} {'--':>12} │")
    lines.append("└" + "─" * 68 + "┘")
    
    lines.append("")
    lines.append("┌" + "─" * 68 + "┐")
    lines.append("│ ANALYSIS NOTES".ljust(69) + "│")
    lines.append("├" + "─" * 68 + "┤")
    
    for r in valid_results:
        if r.analysis:
            lines.append(f"│ {r.method}:".ljust(69) + "│")
            for note in r.analysis[:2]:
                lines.append(f"│   • {note}".ljust(69) + "│")
    
    lines.append("└" + "─" * 68 + "┘")
    lines.append("")
    
    return "\n".join(lines)


def format_summary(results: List[ValuationResult]) -> str:
    valid_results = [r for r in results if r.fair_value > 0]
    
    if not valid_results:
        return "No valid valuation results."
    
    values = [r.fair_value for r in valid_results]
    current_price = results[0].current_price
    
    avg = sum(values) / len(values)
    undervalued = sum(1 for r in valid_results if r.premium_discount > 15)
    
    return (
        f"Summary: {len(valid_results)} methods, "
        f"Average Fair Value: ${avg:.2f}, "
        f"Current: ${current_price:.2f}, "
        f"Upside: {((avg - current_price) / current_price * 100):+.1f}%, "
        f"Undervalued: {undervalued}/{len(valid_results)}"
    )
