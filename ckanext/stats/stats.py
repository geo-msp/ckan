# -*- coding: utf-8 -*-
'''
Contient des fonctions pour collecter les données nécessaires pour
la page statistique avec la base de données.
'''
# -----------Modfication_KRL------------
import datetime
from datetime import datetime as datetime_class
from dateutil.relativedelta import relativedelta
from pylons import config
from sqlalchemy import Table, select, join, func, and_, or_
import json
import urllib3
# -----------Modfication_KRL------------>>

import ckan.plugins as p
import ckan.model as model

cache_enabled = p.toolkit.asbool(config.get('ckanext.stats.cache_enabled', 'True'))

if cache_enabled:
    from pylons import cache

    our_cache = cache.get_cache('stats', type='dbm')

# -----------Modfication_KRL------------
DATE_FORMAT = '%Y-%m-%d'

# Documenter les constantes ou groupes de constantes : utilité

'''
Score associe aux formats
'''
RECOMMENDED_OPEN_FORMAT_SCORE = 1
SECONDARY_OPEN_FORMAT_SCORE = 0.75

'''
Tags
'''
HIGH_VALUE_TAG_NAME = "ville"
MUNICIPAL_TAG_NAME = "Sherbrooke"
OPEN_GOVERNMENT_CANADA_TAG_NAME = "Gouvernement ouvert"
GLOBAL_OPEN_DATA_INDEX_TAG_NAME = "GES"

'''
Le nom d'event dans google analytics
'''
DOWNLOAD_EVENT_NAME = "téléchargement"

PREFIX_URL_DATASET = '/recherche/fr/dataset/'

'''
Paths
'''
PATH_DATA = "https://rc.donneesquebec.ca/wp-content/uploads/stats_data/"
LICENSE_VALUE_PATH = PATH_DATA + "license_values.json"
RECOMMENDED_OPEN_FORMAT_PATH = PATH_DATA + "recommended_open_formats.json"
SECONDARY_OPEN_FORMAT_PATH = PATH_DATA + "secondary_open_formats.json"
NB_ORG_PATH = PATH_DATA + "nb_org_by_type.json"
SCORE_API_REQUEST_PATH = PATH_DATA + "score_api_request.json"
SCORE_DOCUMENTATION_PATH = PATH_DATA + "score_documentation.json"


def get_httprequest_on_path(path):
    http = urllib3.PoolManager()
    req = http.request('GET', path)
    if(req.status == 200):
        response = req.data
    else:
        response = str(req.status)

    return response

'''
Valeur externe pour calculer les scores
'''
license_value = json.loads(get_httprequest_on_path(LICENSE_VALUE_PATH))
recommended_open_format = get_httprequest_on_path(RECOMMENDED_OPEN_FORMAT_PATH)
secondary_open_format = get_httprequest_on_path(SECONDARY_OPEN_FORMAT_PATH)

date_french = {
'January': 'Janvier',
'February': 'Février',
'March': 'Mars',
'April': 'Avril',
'May': 'Mai',
'June': 'Juin',
'July': 'Juillet',
'August': 'Août',
'September': 'Septembre',
'October': 'Octobre',
'November':'Novembre',
'December':'Décembre'
}


# -----------Modfication_KRL------------>>

def table(name):
    return Table(name, model.meta.metadata, autoload=True)


# -----------Modfication_KRL------------
def datetime2date(datetime_):
    return datetime.date(datetime_.year, datetime_.month, datetime_.day)

# -----------Modfication_KRL------------>>

class Stats(object):

    # -----------Modfication_KRL------------
    # Donnees Quebec api



    def nb_of_org_by_type(cls):
        '''
        Utilise l'api de données Québec pour obtenir le nombre d'organisations par type.

        :return: dictionnaire de données avec comme clef le type d'organisation et comme valeur le nombre d'organisation correspondante.
        '''
        return json.loads(get_httprequest_on_path(NB_ORG_PATH))

    def score_api_request(cls):
        '''
        Utilise l'api de données Québec pour obtenir le score sur le nombre de jeux interrogeables par API.

        :return: le nombre de jeux interrogeables par API divisé par le nombre total de jeux.
        '''
        return json.loads(get_httprequest_on_path(SCORE_API_REQUEST_PATH))

    def get_every_month_between_date_and_now(cls, date):
        '''
        Utilise dateutil pour obtenir chaque mois entre la date en paramètre et maintenant.

        :param date: date de format "AAAA-MM-JJ" à partir duquel le calcul est effectué.

        :return: dictionnaire de données contenant chaque mois entre "date" et maintenant
        avec comme clef la date avec ce format : "AAAA-MM-JJ", et comme valeur ce format: Janvier 2018
        '''
        dates = {}

        cur_date = start = datetime_class.strptime(date, '%Y-%m-%d').date()
        end = datetime_class.now().date()

        while cur_date < end:
            dates[cur_date] = date_french[str(cur_date.strftime("%B"))].decode('utf-8') + " " + str(cur_date.year)
            cur_date += relativedelta(months=1)

        dates = sorted(dates.items(), key=lambda kv: kv[0])

        return dates

    def get_every_year_between_date_and_now(cls, date):

        dates = []

        cur_date = start = datetime_class.strptime(date, '%Y-%m-%d').date()
        end = datetime_class.now().date()

        while cur_date < end:
            dates.append(str(cur_date.year))
            cur_date += relativedelta(months=12)

        return dates

    def score_documentation(cls):
        '''
        Utilise l'api de données Québec pour obtenir le score sur le nombre de jeux documentés.

        :return: le nombre de jeux documentés divisé par le nombre total de jeux.
        '''
        return json.loads(get_httprequest_on_path(SCORE_DOCUMENTATION_PATH))

    def score_license(cls):
        '''
        Vérifie directement dans la base de données à l'aide de Sql alchemy la license de chaque jeu de donnees
        et a l'aide du dictionnaire "license_value" on obtient le score associé a la license.

        :return: le score final des licenses divisé par le nombre total de jeux.
        '''
        if type(license_value) is not dict:
            return 0
        license_ids = []
        package = table('package')

        try:
            sql = select([package.c.license_id], from_obj=[package])
            license_ids = model.Session.execute(sql).fetchall()
        except Exception as e:
            print e

        final_score = 0;
        for license in license_ids:
            final_score += license_value.get(str(license.license_id).upper(), 0)

        try:
            final_score = float(final_score) / len(license_ids)
        except ZeroDivisionError:
            return 0

        return final_score

    def score_open_format(cls):
        '''
        Vérifie directement dans la base de données à l'aide de Sql alchemy le format de chaque ressource de chaque jeu de donnees
        et a l'aide de "recommended_open_format" et "secondary_open_format" on obtient le score associé au format.

        :return: le score final des foramts divisé par le nombre total de jeux.
        '''

        resource = table('resource')
        package = table('package')

        res_pkg_ids = []
        final_score = 0;

        try:
            sql = select([package.c.id], from_obj=[package])
            res_pkg_ids = model.Session.execute(sql).fetchall()
        except Exception as e:
            print e

        for pkg in res_pkg_ids:
            res_resource_format = []
            try:
                sql = select([resource.c.format], from_obj=[resource]). \
                    where(resource.c.package_id == pkg.id)
                res_resource_format = model.Session.execute(sql).fetchall()
            except Exception as e:
                print e
            temp_score = 0

            for format in res_resource_format:
                if format.format in recommended_open_format:
                    temp_score = RECOMMENDED_OPEN_FORMAT_SCORE
                    break

            final_score += temp_score

        try:
            final_score = float(final_score) / len(res_pkg_ids)
        except ZeroDivisionError:
            return 0

        return final_score

    # -----------Modfication_KRL------------>>

    @classmethod
    def top_rated_packages(cls, limit=10):
        # NB Not using sqlalchemy as sqla 0.4 doesn't work using both group_by
        # and apply_avg
        package = table('package')
        rating = table('rating')
        sql = select([package.c.id, func.avg(rating.c.rating), func.count(rating.c.rating)],
                     from_obj=[package.join(rating)]). \
            where(and_(package.c.private == False, package.c.state == 'active')). \
            group_by(package.c.id). \
            order_by(func.avg(rating.c.rating).desc(), func.count(rating.c.rating).desc()). \
            limit(limit)
        res_ids = model.Session.execute(sql).fetchall()
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), avg, num) for pkg_id, avg, num in res_ids]
        return res_pkgs

    @classmethod
    def most_edited_packages(cls, limit=10):
        package_revision = table('package_revision')
        package = table('package')

        s = select([package_revision.c.id, func.count(package_revision.c.revision_id)],
                   from_obj=[package_revision.join(package)]). \
            where(and_(package.c.private == False, package.c.state == 'active', )). \
            group_by(package_revision.c.id). \
            order_by(func.count(package_revision.c.revision_id).desc()). \
            limit(limit)
        res_ids = model.Session.execute(s).fetchall()
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), val) for pkg_id, val in res_ids]
        return res_pkgs

    @classmethod
    def largest_groups(cls, limit=10):
        member = table('member')
        package = table('package')

        j = join(member, package,
                 member.c.table_id == package.c.id)

        s = select([member.c.group_id, func.count(member.c.table_id)]). \
            select_from(j). \
            group_by(member.c.group_id). \
            where(and_(member.c.group_id != None, member.c.table_name == 'package', package.c.private == False,
                       package.c.state == 'active')). \
            order_by(func.count(member.c.table_id).desc()). \
            limit(limit)

        res_ids = model.Session.execute(s).fetchall()
        res_groups = [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res_ids]
        return res_groups

    @classmethod
    def top_tags(cls, limit=10, returned_tag_info='object'):  # by package
        assert returned_tag_info in ('name', 'id', 'object')
        tag = table('tag')
        package_tag = table('package_tag')
        package = table('package')
        if returned_tag_info == 'name':
            from_obj = [package_tag.join(tag)]
            tag_column = tag.c.name
        else:
            from_obj = None
            tag_column = package_tag.c.tag_id
        j = join(package_tag, package,
                 package_tag.c.package_id == package.c.id)
        s = select([tag_column, func.count(package_tag.c.package_id)],
                   from_obj=from_obj). \
            select_from(j). \
            where(and_(package_tag.c.state == 'active', package.c.private == False, package.c.state == 'active'))
        s = s.group_by(tag_column). \
            order_by(func.count(package_tag.c.package_id).desc()). \
            limit(limit)
        res_col = model.Session.execute(s).fetchall()
        if returned_tag_info in ('id', 'name'):
            return res_col
        elif returned_tag_info == 'object':
            res_tags = [(model.Session.query(model.Tag).get(unicode(tag_id)), val) for tag_id, val in res_col]
            return res_tags




class RevisionStats(object):
    @classmethod
    def package_addition_rate(cls, weeks_ago=0):
        week_commenced = cls.get_date_weeks_ago(weeks_ago)
        return cls.get_objects_in_a_week(week_commenced,
                                         type_='package_addition_rate')

    @classmethod
    def package_revision_rate(cls, weeks_ago=0):
        week_commenced = cls.get_date_weeks_ago(weeks_ago)
        return cls.get_objects_in_a_week(week_commenced,
                                         type_='package_revision_rate')

    @classmethod
    def get_date_weeks_ago(cls, weeks_ago):
        '''
        @param weeks_ago: specify how many weeks ago to give count for
                          (0 = this week so far)
        '''
        date_ = datetime.date.today()
        return date_ - datetime.timedelta(days=
                                          datetime.date.weekday(date_) + 7 * weeks_ago)

    @classmethod
    def get_week_dates(cls, weeks_ago):
        '''
        @param weeks_ago: specify how many weeks ago to give count for
                          (0 = this week so far)
        '''
        package_revision = table('package_revision')
        revision = table('revision')
        today = datetime.date.today()
        date_from = datetime.datetime(today.year, today.month, today.day) - \
                    datetime.timedelta(days=datetime.date.weekday(today) + \
                                            7 * weeks_ago)
        date_to = date_from + datetime.timedelta(days=7)
        return (date_from, date_to)

    @classmethod
    def get_date_week_started(cls, date_):
        assert isinstance(date_, datetime.date)
        if isinstance(date_, datetime.datetime):
            date_ = datetime2date(date_)
        return date_ - datetime.timedelta(days=datetime.date.weekday(date_))

    @classmethod
    def get_package_revisions(cls):
        '''
        @return: Returns list of revisions and date of them, in
                 format: [(id, date), ...]
        '''
        package_revision = table('package_revision')
        revision = table('revision')
        s = select([package_revision.c.id, revision.c.timestamp], from_obj=[package_revision.join(revision)]).order_by(
            revision.c.timestamp)
        res = model.Session.execute(s).fetchall()  # [(id, datetime), ...]
        return res

    @classmethod
    def get_new_packages(cls):
        '''
        @return: Returns list of new pkgs and date when they were created, in
                 format: [(id, date_ordinal), ...]
        '''

        def new_packages():
            # Can't filter by time in select because 'min' function has to
            # be 'for all time' else you get first revision in the time period.
            package_revision = table('package_revision')
            revision = table('revision')
            s = select([package_revision.c.id, func.min(revision.c.timestamp)],
                       from_obj=[package_revision.join(revision)]).group_by(package_revision.c.id).order_by(
                func.min(revision.c.timestamp))
            res = model.Session.execute(s).fetchall()  # [(id, datetime), ...]
            res_pickleable = []
            for pkg_id, created_datetime in res:
                res_pickleable.append((pkg_id, created_datetime.toordinal()))
            return res_pickleable

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = 'all_new_packages_%s' + week_commences.strftime(DATE_FORMAT)
            new_packages = our_cache.get_value(key=key,
                                               createfunc=new_packages)
        else:
            new_packages = new_packages()
        return new_packages

    @classmethod
    def get_deleted_packages(cls):
        '''
        @return: Returns list of deleted pkgs and date when they were deleted, in
                 format: [(id, date_ordinal), ...]
        '''

        def deleted_packages():
            # Can't filter by time in select because 'min' function has to
            # be 'for all time' else you get first revision in the time period.
            package_revision = table('package_revision')
            revision = table('revision')
            s = select([package_revision.c.id, func.min(revision.c.timestamp)],
                       from_obj=[package_revision.join(revision)]). \
                where(package_revision.c.state == model.State.DELETED). \
                group_by(package_revision.c.id). \
                order_by(func.min(revision.c.timestamp))
            res = model.Session.execute(s).fetchall()  # [(id, datetime), ...]
            res_pickleable = []
            for pkg_id, deleted_datetime in res:
                res_pickleable.append((pkg_id, deleted_datetime.toordinal()))
            return res_pickleable

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = 'all_deleted_packages_%s' + week_commences.strftime(DATE_FORMAT)
            deleted_packages = our_cache.get_value(key=key,
                                                   createfunc=deleted_packages)
        else:
            deleted_packages = deleted_packages()
        return deleted_packages

    @classmethod
    def get_num_packages_by_week(cls):
        def num_packages():
            new_packages_by_week = cls.get_by_week('new_packages')
            deleted_packages_by_week = cls.get_by_week('deleted_packages')
            first_date = (min(datetime.datetime.strptime(new_packages_by_week[0][0], DATE_FORMAT),
                              datetime.datetime.strptime(deleted_packages_by_week[0][0], DATE_FORMAT))).date()
            cls._cumulative_num_pkgs = 0
            new_pkgs = []
            deleted_pkgs = []

            def build_weekly_stats(week_commences, new_pkg_ids, deleted_pkg_ids):
                num_pkgs = len(new_pkg_ids) - len(deleted_pkg_ids)
                new_pkgs.extend([model.Session.query(model.Package).get(id).name for id in new_pkg_ids])
                deleted_pkgs.extend([model.Session.query(model.Package).get(id).name for id in deleted_pkg_ids])
                cls._cumulative_num_pkgs += num_pkgs
                return (week_commences.strftime(DATE_FORMAT),
                        num_pkgs, cls._cumulative_num_pkgs)

            week_ends = first_date
            today = datetime.date.today()
            new_package_week_index = 0
            deleted_package_week_index = 0
            weekly_numbers = []  # [(week_commences, num_packages, cumulative_num_pkgs])]
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                if datetime.datetime.strptime(new_packages_by_week[new_package_week_index][0],
                                              DATE_FORMAT).date() == week_commences:
                    new_pkg_ids = new_packages_by_week[new_package_week_index][1]
                    new_package_week_index += 1
                else:
                    new_pkg_ids = []
                if datetime.datetime.strptime(deleted_packages_by_week[deleted_package_week_index][0],
                                              DATE_FORMAT).date() == week_commences:
                    deleted_pkg_ids = deleted_packages_by_week[deleted_package_week_index][1]
                    deleted_package_week_index += 1
                else:
                    deleted_pkg_ids = []
                weekly_numbers.append(build_weekly_stats(week_commences, new_pkg_ids, deleted_pkg_ids))
            # just check we got to the end of each count
            assert new_package_week_index == len(new_packages_by_week)
            assert deleted_package_week_index == len(deleted_packages_by_week)
            return weekly_numbers

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = 'number_packages_%s' + week_commences.strftime(DATE_FORMAT)
            num_packages = our_cache.get_value(key=key,
                                               createfunc=num_packages)
        else:
            num_packages = num_packages()
        return num_packages

    @classmethod
    def get_by_week(cls, object_type):
        cls._object_type = object_type

        def objects_by_week():
            if cls._object_type == 'new_packages':
                objects = cls.get_new_packages()

                def get_date(object_date):
                    return datetime.date.fromordinal(object_date)
            elif cls._object_type == 'deleted_packages':
                objects = cls.get_deleted_packages()

                def get_date(object_date):
                    return datetime.date.fromordinal(object_date)
            elif cls._object_type == 'package_revisions':
                objects = cls.get_package_revisions()

                def get_date(object_date):
                    return datetime2date(object_date)
            else:
                raise NotImplementedError()
            first_date = get_date(objects[0][1]) if objects else datetime.date.today()
            week_commences = cls.get_date_week_started(first_date)
            week_ends = week_commences + datetime.timedelta(days=7)
            week_index = 0
            weekly_pkg_ids = []  # [(week_commences, [pkg_id1, pkg_id2, ...])]
            pkg_id_stack = []
            cls._cumulative_num_pkgs = 0

            def build_weekly_stats(week_commences, pkg_ids):
                num_pkgs = len(pkg_ids)
                cls._cumulative_num_pkgs += num_pkgs
                return (week_commences.strftime(DATE_FORMAT),
                        pkg_ids, num_pkgs, cls._cumulative_num_pkgs)

            for pkg_id, date_field in objects:
                date_ = get_date(date_field)
                if date_ >= week_ends:
                    weekly_pkg_ids.append(build_weekly_stats(week_commences, pkg_id_stack))
                    pkg_id_stack = []
                    week_commences = week_ends
                    week_ends = week_commences + datetime.timedelta(days=7)
                pkg_id_stack.append(pkg_id)
            weekly_pkg_ids.append(build_weekly_stats(week_commences, pkg_id_stack))
            today = datetime.date.today()
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                weekly_pkg_ids.append(build_weekly_stats(week_commences, []))
            return weekly_pkg_ids

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = '%s_by_week_%s' % (cls._object_type, week_commences.strftime(DATE_FORMAT))
            objects_by_week_ = our_cache.get_value(key=key,
                                                   createfunc=objects_by_week)
        else:
            objects_by_week_ = objects_by_week()
        return objects_by_week_

    @classmethod
    def get_objects_in_a_week(cls, date_week_commences,
                              type_='new-package-rate'):
        '''
        @param type: Specifies what to return about the specified week:
                     "package_addition_rate" number of new packages
                     "package_revision_rate" number of package revisions
                     "new_packages" a list of the packages created
                     in a tuple with the date.
                     "deleted_packages" a list of the packages deleted
                     in a tuple with the date.
        @param dates: date range of interest - a tuple:
                     (start_date, end_date)
        '''
        assert isinstance(date_week_commences, datetime.date)
        if type_ in ('package_addition_rate', 'new_packages'):
            object_type = 'new_packages'
        elif type_ == 'deleted_packages':
            object_type = 'deleted_packages'
        elif type_ == 'package_revision_rate':
            object_type = 'package_revisions'
        else:
            raise NotImplementedError()
        objects_by_week = cls.get_by_week(object_type)
        date_wc_str = date_week_commences.strftime(DATE_FORMAT)
        object_ids = None
        for objects_in_a_week in objects_by_week:
            if objects_in_a_week[0] == date_wc_str:
                object_ids = objects_in_a_week[1]
                break
        if object_ids is None:
            raise TypeError('Week specified is outside range')
        assert isinstance(object_ids, list)
        if type_ in ('package_revision_rate', 'package_addition_rate'):
            return len(object_ids)
        elif type_ in ('new_packages', 'deleted_packages'):
            return [model.Session.query(model.Package).get(pkg_id) \
                    for pkg_id in object_ids]
