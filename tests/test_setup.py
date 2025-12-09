def test_environment_setup():
    """
    Test that ensures the testing environment is correctly set up.
    This is our first 'Red' test because we haven't implemented any logic yet,
    but it verifies we can run tests.
    """
    try:
        import langgraph
        import langchain_openai
    except ImportError:
        assert False, "Required packages (langgraph, langchain-openai) are not installed"

    assert True
