from django.conf import settings


class PrimaryReplicaRouter:
    """SELECT → replica, INSERT/UPDATE/DELETE → primary."""

    def db_for_read(self, model, **hints):
        if settings.DB_READ_FROM_REPLICA:
            return 'replica'
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        dbs = {obj1._state.db, obj2._state.db}
        if dbs <= {'default', 'replica'}:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
