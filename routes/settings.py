from flask import Blueprint, render_template, request, redirect, url_for

from services import storage, cfn_auth

bp = Blueprint('settings', __name__)


@bp.route('/settings')
def index():
    conf = storage.load_all_config()
    return render_template('settings.html', config=conf)


@bp.route('/settings/save_cfn', methods=['POST'])
def save_cfn():
    cookie = request.form.get('cfn_cookie', '')
    user_id = request.form.get('cfn_user_id', '')
    if cookie:
        cfn_auth.save_cookie(cookie)
    if user_id:
        storage.set_config('cfn_user_id', user_id.strip())
    return redirect(url_for('settings.index'))


@bp.route('/settings/toggle_mock', methods=['POST'])
def toggle_mock():
    current = storage.get_config('mock_mode', 'true')
    storage.set_config('mock_mode', 'false' if current == 'true' else 'true')
    return redirect(url_for('settings.index'))


@bp.route('/settings/session/start', methods=['POST'])
def session_start():
    label = request.form.get('label', '')
    storage.start_session(label or None)
    return redirect(url_for('settings.index'))


@bp.route('/settings/session/end', methods=['POST'])
def session_end():
    storage.end_session()
    return redirect(url_for('settings.index'))
