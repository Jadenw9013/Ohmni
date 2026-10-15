"""Tool discovery finds a console install without overriding an explicit PATH choice."""
import pytest

from ohmni.adapters import tools


def test_ngspice_path_precedes_local_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(tools.shutil, 'which', lambda name: '/chosen/ngspice')
    assert tools.find_ngspice() == '/chosen/ngspice'


@pytest.mark.parametrize('name', ['ngspice.exe', 'ngspice_con.exe'])
def test_ngspice_finds_user_console_with_stale_path(monkeypatch, tmp_path, name):
    monkeypatch.setattr(tools.shutil, 'which', lambda _: None)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    executable = tmp_path / 'Programs/ngspice-42/Spice64/bin' / name
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'fixture; never executed')
    assert tools.find_ngspice() == str(executable)


def test_ngspice_gui_and_missing_install_are_not_console_tools(monkeypatch, tmp_path):
    monkeypatch.setattr(tools.shutil, 'which', lambda _: None)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert tools.find_ngspice() is None
    directory = tmp_path / 'Programs/ngspice-42/Spice64/bin'
    directory.mkdir(parents=True)
    (directory / 'ngspice_gui.exe').write_bytes(b'not a console')
    (directory / 'ngspice.exe').mkdir()
    assert tools.find_ngspice() is None


@pytest.mark.parametrize('local', ['', 'relative-folder'])
def test_ngspice_never_discovers_from_an_unset_or_relative_localappdata(monkeypatch, local):
    monkeypatch.setattr(tools.shutil, 'which', lambda _: None)
    monkeypatch.setenv('LOCALAPPDATA', local)
    assert tools.find_ngspice() is None


def test_version_probe_skips_banner_only_lines(monkeypatch):
    from subprocess import CompletedProcess
    monkeypatch.setattr(tools, 'run_tool', lambda *args, **kwargs: CompletedProcess(
        args[0], 0, stdout='******\n** ngspice-42 : Circuit level simulation program\n', stderr=''))
    ok, version = tools._run_version('fixture-console')
    assert ok and 'ngspice-42' in version
