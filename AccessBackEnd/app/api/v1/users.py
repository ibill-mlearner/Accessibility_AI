#
# # Dummy data overview examples -
# @api_v1_bp.get("/student/overview")
# def student_overview_v1():
#     deny = _enforce_roles("student")
#     if deny is not None:
#         return deny
#     return (
#         jsonify(
#             {
#                 "user": _user_context_payload(),
#                 "workspace": {
#                     "active_tools": ["note_taking", "restating", "summaries"],
#                     "next_actions": [
#                         "continue previous study chat",
#                         "review latest class notes",
#                         "start guided prompt",
#                     ],
#                 },
#             }
#         ),
#         200,
#     )
#
# @api_v1_bp.get("/instructor/overview")
# def instructor_overview_v1():
#     deny = _enforce_roles("instructor")
#     if deny is not None:
#         return deny
#     return (
#         jsonify(
#             {
#                 "user": _user_context_payload(),
#                 "workspace": {
#                     "controls": ["prompt_controls", "course_visibility", "feature_toggles"],
#                     "insights": [
#                         "class engagement summary",
#                         "high-friction prompts",
#                         "accommodation usage snapshots",
#                     ],
#                 },
#             }
#         ),
#         200,
#     )
#
#
# @api_v1_bp.get("/admin/overview")
# def admin_overview_v1():
#     deny = _enforce_roles("admin")
#     if deny is not None:
#         return deny
#     return (
#         jsonify(
#             {
#                 "user": _user_context_payload(),
#                 "workspace": {
#                     "controls": ["user_management", "audit_review", "role_assignment"],
#                     "system_health": {
#                         "api": "operational",
#                         "auth": "operational",
#                         "ai_pipeline": "operational",
#                     },
#                 },
#             }
#         ),
#         200,
#     )
# def _user_context_payload() -> dict[str, any]:
#
#     return {
#         "id": current_user.id,
#         "email": current_user.email,
#         "role": current_user.role,
#     }
