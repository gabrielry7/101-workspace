from world_model.restaurant_commerce.campaign_preview_security import secure_preview


def test_preview_uses_fresh_nonce_without_changing_escaped_content():
    markup = '<h1 style="color:red">&lt;p style=&quot;color:blue&quot;&gt;</h1>'
    rendered, policy = secure_preview(markup)
    assert "'unsafe-inline'" not in policy and "'unsafe-hashes'" not in policy
    assert "style-src-attr 'none'" in policy
    assert 'style="' not in rendered
    assert "&lt;p style=&quot;color:blue&quot;&gt;" in rendered
    assert ".preview-style-0{color:red}" in rendered
    assert 'class="preview-style-0"' in rendered
    nonce = rendered.split('nonce="')[1].split('"')[0]
    assert "'nonce-" + nonce + "'" in policy
    assert secure_preview(markup)[1] != policy


def test_preview_style_element_cannot_be_closed_by_a_future_style_value():
    rendered, policy = secure_preview('<h1 style="color:red;&lt;/style&gt;">text</h1>')
    assert rendered.count("</style>") == 1
    assert "\\3c /style\\3e " in rendered
    assert "sandbox allow-same-origin" in policy
