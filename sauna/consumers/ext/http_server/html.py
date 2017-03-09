import datetime

try:
    from html.parser.HTMLParser import escape
except ImportError:
    from html import escape

from . import HTTPServerConsumer
from .dashboard_html import dashboard_html


def get_check_html():
    checks = HTTPServerConsumer.get_checks_as_dict()
    checks_html = ''
    for check_name, data in sorted(checks.items()):
        date = datetime.datetime.fromtimestamp(
            data['timestamp']
        ).strftime('%Y-%m-%d %H:%M:%S')
        checks_html += "<tr>"
        checks_html += "<td>{}</td><td><span class=\"st st_{}\">{}</span>" \
                       "</td><td>{}</td>" \
                       "<td>{}</td>".format(
                        escape(check_name), data['code'], data['status'],
                        escape(data['output']), date)
        checks_html += "</tr>"
    return checks_html


def get_html():
    template = dashboard_html
    checks_html = get_check_html()
    return template.format(checks_html).encode()
