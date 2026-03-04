from flask_login import current_user


class UserContextHelpers:
    @staticmethod
    def _user_context_payload() -> dict[str, any]:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
        }


_user_context_payload = UserContextHelpers._user_context_payload
