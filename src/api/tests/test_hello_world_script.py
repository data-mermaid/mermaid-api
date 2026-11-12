from api.scripts.hello_world import run


def test_hello_world_run_prints_hello_world(capsys):
    run()

    assert capsys.readouterr().out == "hello world\n"
