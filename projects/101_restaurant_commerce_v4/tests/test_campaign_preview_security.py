from world_model.restaurant_commerce.campaign_preview_security import preview_csp


def test_only_real_style_attributes_are_authorized():
    markup = '<h1 style="color:red">&lt;p style=&quot;color:blue&quot;&gt;</h1>'
    policy = preview_csp(markup)
    assert "'unsafe-inline'" not in policy
    assert policy.count("'sha256-") == 1
    assert policy == preview_csp('<h1 style="color:red">different escaped text</h1>')
    assert "style-src 'none'" in preview_csp("<p>No styles</p>")
