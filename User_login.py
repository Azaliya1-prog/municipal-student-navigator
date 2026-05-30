class UserLogin:
    """Объект авторизованного пользователя для Flask-Login."""

    def fromDB(self, user_id, dbase):
        self.__user = dbase.get_user(user_id)
        return self if self.__user else None

    def create(self, user):
        self.__user = user
        return self

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.__user['id'])

    def get_name(self):
        return self.__user['name']

    def get_email(self):
        return self.__user['email']

    def get_role(self):
        return self.__user['role']

    def is_admin(self):
        return self.get_role() == 'admin'
