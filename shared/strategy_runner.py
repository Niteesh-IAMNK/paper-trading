def run_ai(
    strategy,
    portfolio,
    snapshot
):

    if is_analysis_time():
        strategy.generate_signal(
            snapshot
        )

        return

    if is_trading_time():

        signal = strategy.generate_signal(
            snapshot
        )

        execute_trade(
            signal,
            portfolio
        )

        return

    if is_square_off_time():

        force_square_off(
            portfolio
        )