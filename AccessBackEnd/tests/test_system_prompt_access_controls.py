import pytest

from app.extensions import db
from app.db import init_flask_database
from app.models import Accommodation, AccommodationSystemPrompt, CourseClass, SystemPrompt, User


