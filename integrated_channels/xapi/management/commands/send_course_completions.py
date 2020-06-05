# -*- coding: utf-8 -*-
"""
Send xAPI statements to the LRS configured via admin.
"""

from __future__ import absolute_import, unicode_literals

import datetime
from logging import getLogger

import six

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from enterprise.api_client.discovery import get_course_catalog_api_service_client
from enterprise.models import EnterpriseCourseEnrollment, EnterpriseCustomer, EnterpriseCustomerUser
from enterprise.utils import NotConnectedToOpenEdX
from integrated_channels.exceptions import ClientError
from integrated_channels.xapi.models import XAPILearnerDataTransmissionAudit, XAPILRSConfiguration
from integrated_channels.xapi.utils import send_course_completion_statement

try:
    from lms.djangoapps.grades.models import PersistentCourseGrade
except ImportError:
    PersistentCourseGrade = None

try:
    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
except ImportError:
    CourseOverview = None

try:
    from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory  # pylint:disable=ungrouped-imports
except ImportError:
    CourseGradeFactory = None


LOGGER = getLogger(__name__)


class Command(BaseCommand):
    """
    Send course completion xAPI statements to enterprise customers.
    """

    def add_arguments(self, parser):
        """
        Add required arguments to the parser.
        """
        parser.add_argument(
            '--days',
            dest='days',
            required=False,
            type=int,
            default=1,
            help='Send xAPI analytics for learners who enrolled during last this number of days.'
        )
        parser.add_argument(
            '--enterprise_customer_uuid',
            dest='enterprise_customer_uuid',
            type=str,
            required=False,
            help='Send xAPI analytics for this enterprise customer only.'
        )
        super(Command, self).add_arguments(parser)

    @staticmethod
    def parse_arguments(*args, **options):  # pylint: disable=unused-argument
        """
        Parse and validate arguments for the command.

        Arguments:
            *args: Positional arguments passed to the command
            **options: Optional arguments passed to the command

        Returns:
            A tuple containing parsed values for
            1. days (int): Integer showing number of days to lookup enterprise enrollments,
                course completion etc and send to xAPI LRS
            2. enterprise_customer_uuid (EnterpriseCustomer): Enterprise Customer if present then
                send xAPI statements just for this enterprise.
        """
        days = options.get('days', 1)
        enterprise_customer_uuid = options.get('enterprise_customer_uuid')
        enterprise_customer = None

        if enterprise_customer_uuid:
            try:
                # pylint: disable=no-member
                enterprise_customer = EnterpriseCustomer.objects.get(uuid=enterprise_customer_uuid)
            except EnterpriseCustomer.DoesNotExist:
                raise CommandError('Enterprise customer with uuid "{enterprise_customer_uuid}" does not exist.'.format(
                    enterprise_customer_uuid=enterprise_customer_uuid
                ))

        return days, enterprise_customer

    def handle(self, *args, **options):
        """
        Send xAPI statements.
        """
        if not all((PersistentCourseGrade, CourseOverview, CourseGradeFactory)):
            raise NotConnectedToOpenEdX("This package must be installed in an OpenEdX environment.")

        days, enterprise_customer = self.parse_arguments(*args, **options)

        if enterprise_customer:
            try:
                lrs_configuration = XAPILRSConfiguration.objects.get(
                    active=True,
                    enterprise_customer=enterprise_customer
                )
            except XAPILRSConfiguration.DoesNotExist:
                raise CommandError('No xAPI Configuration found for "{enterprise_customer}"'.format(
                    enterprise_customer=enterprise_customer.name
                ))

            # Send xAPI analytics data to the configured LRS
            self.send_xapi_statements(lrs_configuration, days)
        else:
            for lrs_configuration in XAPILRSConfiguration.objects.filter(active=True):
                self.send_xapi_statements(lrs_configuration, days)

    def send_xapi_statements(self, lrs_configuration, days):
        """
        Send xAPI analytics data of the enterprise learners to the given LRS.

        Arguments:
            lrs_configuration (XAPILRSConfiguration): Configuration object containing LRS configurations
                of the LRS where to send xAPI  learner analytics.
        """
        enterprise_course_enrollments = EnterpriseCourseEnrollment.objects.filter(
            enterprise_customer_user_id__enterprise_customer=lrs_configuration.enterprise_customer
        )
        enterprise_course_enrollment_ids = enterprise_course_enrollments.values_list('id', flat=True)

        xapi_transmission_queryset = XAPILearnerDataTransmissionAudit.objects.filter(
            enterprise_course_enrollment_id__in=enterprise_course_enrollment_ids,
            course_completed=0,
        )

        pertinent_enrollment_ids = xapi_transmission_queryset.values_list('enterprise_course_enrollment_id', flat=True)
        pertinent_enrollments = enterprise_course_enrollments.filter(id__in=pertinent_enrollment_ids)
        enrollment_grades = self.get_course_completions(pertinent_enrollments)

        users = self.prefetch_users(enrollment_grades)
        course_overviews = self.prefetch_courses(enrollment_grades)

        course_catalog_client = get_course_catalog_api_service_client(
            site=lrs_configuration.enterprise_customer.site
        )

        for xapi_transmission in xapi_transmission_queryset:

            course_grade = enrollment_grades[xapi_transmission.enterprise_course_enrollment_id]
            user = users.get(course_grade.user_id)
            courserun_id = six.text_type(course_grade.course_id)
            course_overview = course_overviews.get(course_grade.course_id)
            course_overview.key = course_catalog_client.get_course_id(courserun_id)

            response_fields = {'status': 500, 'error_message': None}
            response_fields = send_course_completion_statement(
                lrs_configuration,
                user,
                course_overview,
                course_grade,
                'course',
                response_fields
            )

            if response_fields.get('status') == 200:

                self.save_xapi_learner_data_transmission_audit_record(
                    xapi_transmission,
                    course_grade.percent_grade,
                    1,
                    course_grade.passed_timestamp,
                    response_fields.get('status'),
                    response_fields.get('error_message')
                )

                response_fields = {'status': 500, 'error_message': None}
                response_fields = send_course_completion_statement(
                    lrs_configuration,
                    user,
                    course_overview,
                    course_grade,
                    'courserun',
                    response_fields
                )

                if response_fields.get('status') == 200:

                    self.save_xapi_learner_data_transmission_audit_record(
                        xapi_transmission,
                        course_grade.percent_grade,
                        1,
                        course_grade.passed_timestamp,
                        response_fields.get('status'),
                        response_fields.get('error_message')
                    )

        import pdb; pdb.set_trace();





        # course_catalog_client = get_course_catalog_api_service_client(
        #     site=lrs_configuration.enterprise_customer.site
        # )








        # for persistent_course_grade in persistent_course_grades:

        #     user = users.get(persistent_course_grade.user_id)
        #     course_overview = course_overviews.get(persistent_course_grade.course_id)
        #     course_grade = CourseGradeFactory().read(user, course_key=persistent_course_grade.course_id)
        #     courserun_id = six.text_type(course_overview.id)
        #

        #     enterprise_course_enrollment_id = EnterpriseCourseEnrollment.get_enterprise_course_enrollment_id(
        #         user,
        #         courserun_id,
        #         lrs_configuration.enterprise_customer
        #     )

        #     import pdb; pdb.set_trace()
        #     enterprise_course_enrollments = EnterpriseCourseEnrollment.objects.filter(enterprise_customer_user_id__enterprise_customer=lrs_configuration.enterprise_customer)
        #     enterprise_enrollment_ids = enterprise_course_enrollments.values_list('user_id', flat=True)
        #     xapi_transmission_queryset = XAPILearnerDataTransmissionAudit.objects.filter(
        #         course_completed=0,
        #         enterprise_course_enrollment_id__in=enterprise_enrollment_ids
        #     )
        #     if not xapi_transmission_queryset.exists():
        #         LOGGER.warning(
        #             'XAPILearnerDataTransmissionAudit object does not exist for enterprise customer: '
        #             '{enterprise_customer}, user: {username}, course: {course_id}.  Skipping transmission '
        #             'of course completion statement to the configured LRS endpoint.  This is likely because '
        #             'a corresponding course enrollment statement has not yet been transmitted.'.format(
        #                 enterprise_customer=lrs_configuration.enterprise_customer.name,
        #                 username=user.username if user else 'User Unavailable',
        #                 course_id=six.text_type(course_overview.id)
        #             )
        #         )
        #         continue

        #     response_fields = {'status': 500, 'error_message': None}
        #     response_fields = send_course_completion_statement(
        #         lrs_configuration,
        #         user,
        #         course_overview,
        #         course_grade,
        #         'course',
        #         response_fields
        #     )

        #     course_completed = 0
        #     if response_fields.get('status') == 200:
        #         course_completed = 1

        #     self.save_xapi_learner_data_transmission_audit_record(
        #         user,
        #         course_overview.key,
        #         enterprise_course_enrollment_id,
        #         course_grade.percent,
        #         course_completed,
        #         persistent_course_grade.modified,
        #         response_fields.get('status'),
        #         response_fields.get('error_message')

        #     )

        #     response_fields = {'status': 500, 'error_message': None}
        #     response_fields = send_course_completion_statement(
        #         lrs_configuration,
        #         user,
        #         course_overview,
        #         "courserun",
        #         response_fields
        #     )

        #     course_completed = 0
        #     if response_fields.get('status') == 200:
        #         course_completed = 1

        #         self.save_xapi_learner_data_transmission_audit_record(
        #             user,
        #             courserun_id,
        #             enterprise_course_enrollment_id,
        #             course_grade.percent,
        #             course_completed,
        #             persistent_course_grade.modified,
        #             response_fields.get('status'),
        #             response_fields.get('error_message')
        #         )

    def get_course_completions(self, enterprise_course_enrollments):
        """
        Get course completions via PersistentCourseGrade for all the learners of given enterprise customer.

        Arguments:
            enterprise_customer (EnterpriseCustomer): Include Course enrollments for learners
                of this enterprise customer.
            days (int): Include course enrollment of this number of days.

        Returns:
            (list): A list of PersistentCourseGrade objects.

        """
        ece_grades = {}

        for ece in enterprise_course_enrollments:

            lms_user_id = EnterpriseCustomerUser.objects.get(id=ece.enterprise_customer_user_id).user_id
            grade_records = PersistentCourseGrade.objects.filter(
                user_id=lms_user_id,
                course_id=ece.course_id,
                passed_timestamp__isnull=False
            )

            if len(grade_records):
                ece_grades.setdefault(ece.id, grade_records.first())

        return ece_grades

    @staticmethod
    def prefetch_users(enterprise_course_enrollment_grades):
        """
        Prefetch Users from the list of user_ids present in the persistent_course_grades.

        Arguments:
            persistent_course_grades (list): A list of PersistentCourseGrade.

        Returns:
            (dict): A dictionary containing user_id to user mapping.
        """
        users = User.objects.filter(
            id__in=[ece_grade.user_id for ece_grade in enterprise_course_enrollment_grades.values()]
        )
        return {
            user.id: user for user in users
        }

    @staticmethod
    def prefetch_courses(enterprise_course_enrollment_grades):
        """
        Prefetch courses from the list of course_ids present in the persistent_course_grades.

        Arguments:
            persistent_course_grades (list): A list of PersistentCourseGrade.

        Returns:
            (dict): A dictionary containing course_id to course_overview mapping.
        """
        return CourseOverview.get_from_ids(
            [ece_grade.course_id for ece_grade in enterprise_course_enrollment_grades.values()]
        )

    def save_xapi_learner_data_transmission_audit_record(self, xapi_transmission,
                                                         course_grade, course_completed, completed_timestamp,
                                                         status, error_message):
        xapi_transmission.course_completed = course_completed
        xapi_transmission.completed_timestamp = completed_timestamp
        xapi_transmission.course_grade = course_grade
        xapi_transmission.status = status
        xapi_transmission.error_message = error_message
        xapi_transmission.save()

        LOGGER.info(
            "Successfully updated the XAPILearnerDataTransmissionAudit object with id: {id}, user: {username}"
            " and course: {course_id}".format(
                id=xapi_transmission.id,
                username=xapi_transmission.user.username,
                course_id=xapi_transmission.course_id
            )
        )