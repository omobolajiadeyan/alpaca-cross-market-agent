from compliance.audit_logger import AuditLogger


def test_trade_status_reflects_execution(tmp_path):
    logger = AuditLogger(str(tmp_path / 'audit.db'))
    thesis_id = logger.log_thesis({'thesis': 'x'})
    portfolio = {
        'primary_trade': {'strategy': 'a', 'execution': {'submitted': True}},
        'secondary_trade': {'execution': {'submitted': True}},
        'hedge': {'execution': {'submitted': True}},
    }
    logger.log_trade(thesis_id, portfolio)
    assert logger.get_dashboard_data()['trades'][0]['status'] == 'submitted'
