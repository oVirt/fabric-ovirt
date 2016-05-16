import fabric_ovirt.lib.utils


def test_html_to_text_good():
    expected1 = 'WORK:nobody - '
    expected2 = 'WORK:user2 - 2035-01-30 - Blabla blah (failed to add host)'
    html = '\r\n'.join([
        '<pre>',
        '    <a href=mailto:user1@dmain.com?subject=job%20x'
        + '&body=WORK%3Anobody%20-%20>WORK:nobody</a> - ',
        '    <a href=mailto:user2@domain.com?subject=job%20y'
        + '&body=WORK%3Auser2%20-%20>WORK:user2</a>'
        + ' - 2035-01-30 - Blabla blah (failed to add host)',
        '</pre>',
    ])
    expected = '\r\n'.join([
        '',
        '    ' + expected1,
        '    ' + expected2,
        '',

    ])
    actual = fabric_ovirt.lib.utils.html_to_text(html)
    assert expected == actual


def test_html_to_text_bad():
    """
    tests broken html stripping works ok
    """
    expected1 = 'WORK:nobody - '
    expected2 = 'WORK:user2 - 2035-01-30 - Blabla blah (failed to add host)'
    html = '\r\n'.join([
        '    <a href=mailto:user1@dmain.com?subject=job%20x'
        + '&body=WORK%3Anobody%20-%20>WORK:nobody</a> - ',
        '    <a href=mailto:user2@domain.com?subject=job%20y'
        + '&body=WORK%3Auser2%20-%20>WORK:user2</a> - '
        + '2035-01-30 - Blabla blah (failed to add host)',
        '</pre',
    ])
    expected = '\r\n'.join([
        '    ' + expected1,
        '    ' + expected2,
        '',
    ])
    actual = fabric_ovirt.lib.utils.html_to_text(html)
    assert expected == actual
