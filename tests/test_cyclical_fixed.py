# Fixed test for cyclical PB valuation at TOP phase
stock = CyclicalStock(
    ticker="601919",
    name="中远海控",
    market=MarketType.A_SHARE,
    current_price=30.0,
    cycle_type=CycleType.SHIPPING,
    current_phase=CyclePhase.TOP,
    pb=3.2,  # Greater than sell threshold of 3.0
    bvps=14.5,
    historical_pb=[1.5, 2.0, 1.8, 2.5, 1.2],
)

valuation = CyclicalPBValuation()
result = valuation.calculate(stock)

assert result.action == "SELL"
print("✓ Test passed: TOP phase with PB 3.2 should SELL")
