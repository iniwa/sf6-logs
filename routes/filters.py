from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def register_filters(app):

    @app.template_filter('format_datetime')
    def format_datetime(iso_str):
        if not iso_str:
            return ''
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime('%m/%d %H:%M')
        except (ValueError, TypeError):
            return str(iso_str)

    @app.template_filter('result_icon')
    def result_icon(result):
        if result == 'win':
            return 'W'
        elif result == 'lose':
            return 'L'
        return '?'

    @app.template_filter('result_class')
    def result_class(result):
        if result == 'win':
            return 'result-win'
        elif result == 'lose':
            return 'result-lose'
        return ''

    @app.template_filter('lp_change')
    def lp_change(match):
        # MASTER の場合は MR の変動を表示
        if match.get('mr_after') is not None:
            before = match.get('mr_before')
            after = match.get('mr_after')
        else:
            before = match.get('lp_before')
            after = match.get('lp_after')
        if before is None or after is None:
            return ''
        diff = after - before
        if diff > 0:
            return f'+{diff}'
        return str(diff)
