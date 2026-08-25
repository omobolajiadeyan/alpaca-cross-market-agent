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


def test_decision_contract_is_persisted_and_linked(tmp_path):
    logger = AuditLogger(str(tmp_path / 'audit.db'))
    contract = {
        'contract_id': 'CS-TEST', 'decision_hash': 'abc123',
        'created_at': '2026-08-25T12:00:00Z', 'authorization': 'AUTHORIZED',
    }
    logger.log_decision_contract(contract)
    logger.link_contract_execution('CS-TEST', 7, 'filled')
    row = logger.get_dashboard_data()['contracts'][0]
    assert row['execution_status'] == 'filled'
    assert row['trade_id'] == 7
