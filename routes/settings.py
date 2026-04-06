from flask import Blueprint, render_template, request, redirect, url_for

from services import storage, cfn_auth

bp = Blueprint('settings', __name__)


@bp.route('/settings')
def index():
    conf = storage.load_all_config()
    return render_template('settings.html', config=conf)


@bp.route('/overlay-settings')
def overlay_settings():
    conf = storage.load_all_config()
    session = storage.get_current_session()
    return render_template('overlay_settings.html', config=conf, session=session)


@bp.route('/settings/save_cfn', methods=['POST'])
def save_cfn():
    cookie = request.form.get('cfn_cookie', '')
    user_id = request.form.get('cfn_user_id', '')
    if cookie:
        cfn_auth.save_cookie(cookie)
    if user_id:
        storage.set_config('cfn_user_id', user_id.strip())
    return redirect(url_for('settings.index'))


@bp.route('/settings/save_capcom_id', methods=['POST'])
def save_capcom_id():
    email = request.form.get('capcom_email', '').strip()
    password = request.form.get('capcom_password', '').strip()
    if email:
        storage.set_config('capcom_email', email)
    if password:
        storage.set_config('capcom_password', password)
    return redirect(url_for('settings.index'))


@bp.route('/settings/test_login', methods=['POST'])
def test_login():
    """自動ログインをテスト実行"""
    try:
        cfn_auth.auto_login()
        return redirect(url_for('settings.index', msg='login_ok'))
    except Exception as e:
        return redirect(url_for('settings.index', msg='login_fail', detail=str(e)))


@bp.route('/settings/toggle_mock', methods=['POST'])
def toggle_mock():
    current = storage.get_config('mock_mode', 'true')
    new_value = 'false' if current == 'true' else 'true'
    storage.set_config('mock_mode', new_value)
    if new_value == 'false':
        storage.delete_mock_matches()
    return redirect(url_for('settings.index'))


@bp.route('/settings/session/start', methods=['POST'])
def session_start():
    label = request.form.get('label', '')
    storage.start_session(label or None)
    return redirect(url_for('settings.overlay_settings'))


@bp.route('/settings/session/end', methods=['POST'])
def session_end():
    storage.end_session()
    return redirect(url_for('settings.overlay_settings'))
