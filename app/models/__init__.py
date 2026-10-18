"""Model package.

Importing every model here guarantees they are all registered on `Base` before
Alembic autogenerates a migration, so no table is ever missed.
"""

from .user import User
from .property import Property
from .room import Room
from .booking import Booking
from .payment import Payment
from .review import Review
