# -*- coding: utf-8 -*-

import pytest
import mock

from h import models
from h.admin.views import features as views


class DummyFeature(object):
    def __init__(self, name):
        self.name = name
        self.everyone = False
        self.admins = False
        self.staff = False


features_save_fixtures = pytest.mark.usefixtures('Feature',
                                                 'check_csrf_token')


@features_save_fixtures
def test_features_save_sets_attributes_when_checkboxes_on(Feature, pyramid_request):
    foo = DummyFeature(name='foo')
    bar = DummyFeature(name='bar')
    Feature.all.return_value = [foo, bar]
    pyramid_request.POST = {'foo[everyone]': 'on',
                            'foo[staff]': 'on',
                            'bar[admins]': 'on'}

    views.features_save(pyramid_request)

    assert foo.everyone == foo.staff == bar.admins == True


@features_save_fixtures
def test_features_save_sets_attributes_when_checkboxes_off(Feature, pyramid_request):
    foo = DummyFeature(name='foo')
    foo.everyone = True
    foo.staff = True
    Feature.all.return_value = [foo]
    pyramid_request.POST = {}

    views.features_save(pyramid_request)

    assert foo.everyone == foo.staff == False


@features_save_fixtures
def test_features_save_ignores_unknown_fields(Feature, pyramid_request):
    foo = DummyFeature(name='foo')
    Feature.all.return_value = [foo]
    pyramid_request.POST = {'foo[wibble]': 'on',
                            'foo[admins]': 'ignoreme'}

    views.features_save(pyramid_request)

    assert foo.admins == False


@features_save_fixtures
def test_features_save_checks_csrf_token(Feature, check_csrf_token, pyramid_request):
    Feature.all.return_value = []
    pyramid_request.POST = {}

    views.features_save(pyramid_request)

    check_csrf_token.assert_called_with(pyramid_request)


def test_cohorts_index_without_cohorts(pyramid_request):
    result = views.cohorts_index({}, pyramid_request)
    assert result["results"] == []


def test_cohorts_index_with_cohorts(pyramid_request):
    cohort1 = models.FeatureCohort(name='cohort1')
    cohort2 = models.FeatureCohort(name='cohort2')
    pyramid_request.db.add(cohort1)
    pyramid_request.db.add(cohort2)
    pyramid_request.db.flush()

    result = views.cohorts_index({}, pyramid_request)
    assert len(result["results"]) == 2


def test_cohorts_add_creates_cohort_with_no_members(pyramid_request):
    pyramid_request.params['add'] = 'cohort'
    views.cohorts_add(pyramid_request)

    result = pyramid_request.db.query(models.FeatureCohort).filter_by(name='cohort').all()
    assert len(result) == 1

    cohort = result[0]
    assert cohort.name == "cohort"
    assert len(cohort.members) == 0


def test_cohorts_edit_add_user(factories, pyramid_request):
    user = factories.User(username='benoit')
    cohort = models.FeatureCohort(name='FractalCohort')

    pyramid_request.db.add(user)
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    pyramid_request.matchdict['id'] = cohort.id
    pyramid_request.params['add'] = user.username
    views.cohorts_edit_add(pyramid_request)

    assert len(cohort.members) == 1
    assert cohort.members[0].username == user.username


def test_cohorts_edit_remove_user(factories, pyramid_request):
    user = factories.User(username='benoit')
    cohort = models.FeatureCohort(name='FractalCohort')
    cohort.members.append(user)

    pyramid_request.db.add(user)
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    assert len(cohort.members) == 1

    pyramid_request.matchdict['id'] = cohort.id
    pyramid_request.params['remove'] = user.username
    views.cohorts_edit_remove(pyramid_request)

    assert len(cohort.members) == 0


def test_cohorts_edit_with_no_users(pyramid_request):
    cohort = models.FeatureCohort(name='FractalCohort')
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    pyramid_request.matchdict['id'] = cohort.id
    result = views.cohorts_edit({}, pyramid_request)

    assert result['cohort'].id == cohort.id
    assert len(result['cohort'].members) == 0


def test_cohorts_edit_with_users(factories, pyramid_request):
    cohort = models.FeatureCohort(name='FractalCohort')
    user1 = factories.User(username='benoit')
    user2 = factories.User(username='emily')
    cohort.members.append(user1)
    cohort.members.append(user2)

    pyramid_request.db.add(user1)
    pyramid_request.db.add(user2)
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    pyramid_request.matchdict['id'] = cohort.id
    result = views.cohorts_edit({}, pyramid_request)

    assert result['cohort'].id == cohort.id
    assert len(result['cohort'].members) == 2


@pytest.mark.usefixtures('check_csrf_token')
@mock.patch.dict('h.features.models.FEATURES', {'feat': 'A test feature'})
def test_features_save_sets_cohorts_when_checkboxes_on(pyramid_request):
    feat = models.Feature(name='feat')
    cohort = models.FeatureCohort(name='cohort')

    pyramid_request.db.add(feat)
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    pyramid_request.POST = {'feat[cohorts][cohort]': 'on'}
    views.features_save(pyramid_request)

    feat = pyramid_request.db.query(models.Feature).filter_by(name='feat').first()
    cohort = pyramid_request.db.query(models.FeatureCohort).filter_by(name='cohort').first()

    assert len(feat.cohorts) == 1
    assert cohort in feat.cohorts


@pytest.mark.usefixtures('check_csrf_token')
@mock.patch.dict('h.features.models.FEATURES', {'feat': 'A test feature'})
def test_features_save_unsets_cohorts_when_checkboxes_off(pyramid_request):
    feat = models.Feature(name='feat')
    cohort = models.FeatureCohort(name='cohort')
    feat.cohorts.append(cohort)

    pyramid_request.db.add(feat)
    pyramid_request.db.add(cohort)
    pyramid_request.db.flush()

    pyramid_request.POST = {'feat[cohorts][cohort]': 'off'}
    views.features_save(pyramid_request)

    feat = pyramid_request.db.query(models.Feature).filter_by(name='feat').first()
    cohort = pyramid_request.db.query(models.FeatureCohort).filter_by(name='cohort').first()

    assert len(feat.cohorts) == 0
    assert cohort not in feat.cohorts


@pytest.fixture(autouse=True)
def routes(pyramid_config):
    pyramid_config.add_route('admin_features', '/adm/features')
    pyramid_config.add_route('admin_cohorts', '/adm/cohorts')
    pyramid_config.add_route('admin_cohorts_edit', '/adm/cohorts/{id}')


@pytest.fixture
def Feature(patch):
    return patch('h.models.Feature')


@pytest.fixture
def check_csrf_token(patch):
    return patch('pyramid.session.check_csrf_token')
