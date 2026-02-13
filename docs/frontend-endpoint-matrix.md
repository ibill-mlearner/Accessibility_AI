# Frontend Implementation Matrix from API View Templates

Source templates: `AccessBackEnd/app/templates/api_view/endpoints/`.

## Frontend Screen ↔ Resource Mapping (current)

| Frontend screen/workflow | Resource(s) | Evidence |
|---|---|---|
| `ClassesView.vue` | `classes` | Renders `store.roleClasses`, which is derived from `store.classes`. |
| `AccessibilityView.vue` | `features` | Renders `store.features`. |
| `SavedNotesView.vue` | `notes` | Renders `store.notes`. |
| Home/chat workflow (`HomeView.vue` + app bootstrap) | `chats`, `messages`, `ai/interactions` | `store.bootstrap()` fetches `chats`; `messages` and `ai/interactions` are part of the chat domain in backend templates and should be wired in chat flow. |

## Endpoint Matrix (template-aligned)

> **Pass-through warning:** Collection `POST` and item `PUT/PATCH` operations store/replace payloads as-is. Frontend should send complete record shape (including any fields it needs preserved).

| Resource | Method | Path | Request body shape (from template) | Response shape example (from template) | Pass-through / replacement behavior |
|---|---|---|---|---|---|
| health | GET | `/api/v1/health` | _None_ | `{"status":"ok","ai_provider":"mock_json"}` | No |
| ai/interactions | POST | `/api/v1/ai/interactions` | `{"prompt":"hello","system_prompt":"optional","rag":{"source":"optional"}}` | Provider-backed AI response metadata (template text; no concrete response JSON shown). | No explicit pass-through note |
| chats (collection) | GET | `/api/v1/chats` | _None_ | `{"id":99,"title":"Chat 99","meta":{"tag":"passthrough"}}` | N/A |
| chats (collection) | POST | `/api/v1/chats` | `{"id":99,"title":"Chat 99","meta":{"tag":"passthrough"}}` | `{"id":99,"title":"Chat 99","meta":{"tag":"passthrough"}}` | **Yes**: stores JSON object as-is |
| chats (item) | GET | `/api/v1/chats/<id>` | _None_ | `{"id":1,"title":"Renamed Chat","extra":["a","b"]}` | N/A |
| chats (item) | PUT/PATCH | `/api/v1/chats/<id>` | `{"id":1,"title":"Renamed Chat","extra":["a","b"]}` | `{"id":1,"title":"Renamed Chat","extra":["a","b"]}` | **Yes**: replaces full record |
| chats (item) | DELETE | `/api/v1/chats/<id>` | _None_ | Returns deleted object (example shape above). | N/A |
| messages (collection) | GET | `/api/v1/messages` | _None_ | `{"id":4,"chat_id":1,"message_text":"What is ATP?","vote":"good","note":"yes","help_intent":"summarization"}` | N/A |
| messages (collection) | POST | `/api/v1/messages` | `{"id":4,"chat_id":1,"message_text":"What is ATP?","vote":"good","note":"yes","help_intent":"summarization"}` | `{"id":4,"chat_id":1,"message_text":"What is ATP?","vote":"good","note":"yes","help_intent":"summarization"}` | **Yes**: appends without transformation |
| messages (item) | GET | `/api/v1/messages/<id>` | _None_ | `{"id":2,"chat_id":1,"message_text":"Updated text","vote":"good","note":"no","help_intent":"note_taking"}` | N/A |
| messages (item) | PUT/PATCH | `/api/v1/messages/<id>` | `{"id":2,"chat_id":1,"message_text":"Updated text","vote":"good","note":"no","help_intent":"note_taking"}` | `{"id":2,"chat_id":1,"message_text":"Updated text","vote":"good","note":"no","help_intent":"note_taking"}` | **Yes**: replaces targeted record exactly |
| messages (item) | DELETE | `/api/v1/messages/<id>` | _None_ | Returns deleted object (example shape above). | N/A |
| classes (collection) | GET | `/api/v1/classes` | _None_ | `{"id":7,"role":"student","name":"Physics 110","description":"Guided support for class material"}` | N/A |
| classes (collection) | POST | `/api/v1/classes` | `{"id":7,"role":"student","name":"Physics 110","description":"Guided support for class material"}` | `{"id":7,"role":"student","name":"Physics 110","description":"Guided support for class material"}` | **Yes**: stores directly |
| classes (item) | GET | `/api/v1/classes/<id>` | _None_ | `{"id":1,"role":"student","name":"Biology 103","description":"Updated class description"}` | N/A |
| classes (item) | PUT/PATCH | `/api/v1/classes/<id>` | `{"id":1,"role":"student","name":"Biology 103","description":"Updated class description"}` | `{"id":1,"role":"student","name":"Biology 103","description":"Updated class description"}` | **Yes**: overwrite with provided JSON |
| classes (item) | DELETE | `/api/v1/classes/<id>` | _None_ | Returns deleted payload (example shape above). | N/A |
| notes (collection) | GET | `/api/v1/notes` | _None_ | `{"id":3,"class":"Bio","date":"2026-02-10","chat":"Chat 4","content":"Cell respiration summary"}` | N/A |
| notes (collection) | POST | `/api/v1/notes` | `{"id":3,"class":"Bio","date":"2026-02-10","chat":"Chat 4","content":"Cell respiration summary"}` | `{"id":3,"class":"Bio","date":"2026-02-10","chat":"Chat 4","content":"Cell respiration summary"}` | **Yes**: appends exactly as submitted |
| notes (item) | GET | `/api/v1/notes/<id>` | _None_ | `{"id":1,"class":"Bio","date":"2026-02-09","chat":"Chat 3","content":"Updated note content"}` | N/A |
| notes (item) | PUT/PATCH | `/api/v1/notes/<id>` | `{"id":1,"class":"Bio","date":"2026-02-09","chat":"Chat 3","content":"Updated note content"}` | `{"id":1,"class":"Bio","date":"2026-02-09","chat":"Chat 3","content":"Updated note content"}` | **Yes**: replaces entire note record |
| notes (item) | DELETE | `/api/v1/notes/<id>` | _None_ | Returns deleted object (example shape above). | N/A |
| features (collection) | GET | `/api/v1/features` | _None_ | `{"id":4,"title":"Outline mode","description":"Concise bulleted responses","enabled":true,"instructor_id":4,"class_id":1}` | N/A |
| features (collection) | POST | `/api/v1/features` | `{"id":4,"title":"Outline mode","description":"Concise bulleted responses","enabled":true,"instructor_id":4,"class_id":1}` | `{"id":4,"title":"Outline mode","description":"Concise bulleted responses","enabled":true,"instructor_id":4,"class_id":1}` | **Yes**: creates from provided JSON object |
| features (item) | GET | `/api/v1/features/<id>` | _None_ | `{"id":2,"title":"Summarization and restating","description":"Responses focused on summaries","enabled":false,"instructor_id":5,"class_id":2}` | N/A |
| features (item) | PUT/PATCH | `/api/v1/features/<id>` | `{"id":2,"title":"Summarization and restating","description":"Responses focused on summaries","enabled":false,"instructor_id":5,"class_id":2}` | `{"id":2,"title":"Summarization and restating","description":"Responses focused on summaries","enabled":false,"instructor_id":5,"class_id":2}` | **Yes**: replace feature record |
| features (item) | DELETE | `/api/v1/features/<id>` | _None_ | Returns removed feature object (example shape above). | N/A |

## Frontend payload guidance for pass-through endpoints

- For `POST` collection endpoints, backend stores object bodies without normalization/transforms.
- For `PUT/PATCH` item endpoints, backend replaces full record with payload object.
- Frontend should send **complete records** (not sparse patches) unless intentionally dropping omitted fields.
