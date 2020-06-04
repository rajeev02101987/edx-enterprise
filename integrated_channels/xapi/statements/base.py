# -*- coding: utf-8 -*-

"""
Statements base for xAPI.
"""
from __future__ import absolute_import, unicode_literals

from tincan import Activity, ActivityDefinition, Agent, LanguageMap, Statement

from integrated_channels.xapi.constants import X_API_ACTIVITY_COURSE


class EnterpriseStatement(Statement):
    """
    Base statement for enterprise events.
    """

    def _get_actor_name(self, user, user_social_auth):
        """
        Returns the name of the actor based on provided information and defined rules

        Arguments:
            user (User): User.
            user_social_auth (UserSocialAuth): UserSocialAuth.
        """
        social_auth_uid = user_social_auth.uid if user_social_auth else ''
        sso_id = social_auth_uid.split(':')[-1]
        actor_name = sso_id if sso_id else user.email
        return actor_name


    def get_actor(self, user, user_social_auth):
        """
        Returns the actor component of the Enterprise xAPI statement.
        Arguments:
            user (User): User.
            user_social_auth (UserSocialAuth): UserSocialAuth.
        """
        name = self._get_actor_name(user, user_social_auth)
        return Agent(
            name=name,
            mbox=u'mailto:{email}'.format(email=user.email),
        )

    def get_object(self, course_overview, object_type):
        """
        Returns the object (activity) component of the Enterprise xAPI statement.
        Arguments:
            course_overview (CourseOverview): CourseOverview.
            object_type (string): Object type for activity.
        """
        name = (course_overview.display_name or '').encode("ascii", "ignore").decode('ascii')

        description = (course_overview.short_description or '').encode("ascii", "ignore").decode('ascii')

        course_id = course_overview.id
        if object_type is not None and object_type == 'course':
            course_id = course_overview.key

        from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
        activity_id = 'https://{activity_domain}/xapi/activities/{course_id}'.format(
            activity_domain=configuration_helpers.get_value('SITE_NAME'),
            course_id=course_id
        )

        return Activity(
            id=activity_id,
            definition=ActivityDefinition(
                type=X_API_ACTIVITY_COURSE,
                name=LanguageMap({'en-US': name}),
                description=LanguageMap({'en-US': description}),
            ),
        )
