from simplisafe_apple_home.errors import http_status, safe_error_message


class ResponseError(Exception):
    status = 400

    def __repr__(self) -> str:
        return "ResponseError(Authorization='Bearer secret-token')"


class RequestError(Exception):
    pass


def test_safe_error_message_does_not_render_wrapped_request() -> None:
    error = RequestError(ResponseError())

    message = safe_error_message(error)

    assert message == "RequestError (HTTP 400)"
    assert http_status(error) == 400
    assert "secret-token" not in message
