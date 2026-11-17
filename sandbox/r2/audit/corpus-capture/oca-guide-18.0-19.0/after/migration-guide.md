# Before migrating

* Update yourself with the latest OCA Conventions: https://odoo-community.org/page/contributing
* Subscribe to the mailing list of the related project: https://odoo-community.org/groups
* On the corresponding GitHub issue named "Migration to version 19.0", announce which module(s) you want to migrate
* [[Install pre-commit]]

# Tasks to do in the migration

**REMARK:** Here, we are highlighting **framework changes** from previous version to this one, not data-model changes, as they are very extensive, and the alternative may depends on the module requirements, nor business methods changes. You can check data-model changes for each core module in the `upgrade_analysis.txt` files inside OpenUpgrade project: https://github.com/OCA/OpenUpgrade.

**REMARK 2**: If you are doing a migration jumping several versions, please check all the tasks in the successive "Migration to version XX.0" guides until arriving to this one.

* Bump module version to `19.0.1.0.0`.
* Remove any possible migration script from previous version (in a nutshell, remove `migrations` folder inside the module if exists).
* Remove references in CREDITS.rst of past financed migrations by other companies.
* If you are comfortable with squashing commits in Git, you could consider to squash administrative commits (if any) with the previous commit for reducing commit noise. Check https://github.com/OCA/maintainer-tools/wiki/Merge-commits-in-pull-requests#mergesquash-the-commits-generated-by-bots-or-weblate for details.
* On `res.groups`, `category_id` field disappears, replaced by the new field `privilege_id`, which points to a new model `res.groups.privilege`, that you may need to create as well if you are defining a new permission section. More info at https://github.com/odoo/odoo/commit/33637d137ed52f5faabaafd5c208e187042be8eb.
* On views, menus, actions, reports definition or some more, replace the `groups_id` field by `group_ids`. Specifically, the technical models with this change are `res.users`, `ir.ui.view`, `ir.ui.menu`, `ir.actions`, `ir.actions.report` and `website.page.properties`. More info at [odoo/odoo#179354](https://github.com/odoo/odoo/pull/179354).
* Replace the following internal variables: `self._cr` -> `self.env.cr`, `self._uid` -> `self.env.uid`, `self._context` -> `self.env.context`.
* Replace `odoo.osv.expression` by `odoo.fields.Domain` expressions. More info at [odoo/odoo#217708](https://github.com/odoo/odoo/pull/217708).
* Replace the `_sql_constraints` model variable by new variables instantiating `models.Constraint` or `models.Index`. More info at [odoo/odoo#175783](https://github.com/odoo/odoo/pull/175783).
* Replace manual timezone manipulations (using pytz, `self.env.context.get("tz")`, etc), by the new `self.env.tz` timezone reference. Check more details in [odoo/odoo#221541](https://github.com/odoo/odoo/pull/221541).
* On the fields definitions, replace the parameter `auto_join` by `bypass_search_access`. More info at [odoo/odoo#219627](https://github.com/odoo/odoo/pull/219627).
* Replace `read_group` by `_read_group` (if a backend process) or `formatted_read_group` (if public call). More info at [odoo/odoo#163300](https://github.com/odoo/odoo/pull/163300).
* On the controllers, replace `type="json"` by `type="jsonrpc"` on the `@route` decorator definition. More info at [odoo/odoo#183636](https://github.com/odoo/odoo/pull/183636).
* Search methods of computed non stored fields now should return a `Domain` object instead of the classical list. More info at [odoo/odoo@4f0d4670ed](https://github.com/odoo/odoo/commit/4f0d4670edea0e989fc939e3b2e75cefd351cfc3).
* In the same mood, if overriding any of these search methods, and wanting to introspect the arguments of the search (`operator` and `value`), you may take into account that the domain passed in the original search may not match, because the domain optimizer may change it. Example: having a search over a boolean field this way: `model.search([("boolean_field", "=", True)])`, the method `_search_boolean_field` will receive as operator `in` (not `=`) and as value `OrderedSet([True])`, not `True`.
* In general, you can replace the use of traditional domains with lists by `Domain` objects (in searches, filtered_domain, etc), for clearer syntax and better optimization. Example: [OCA/commission#646](https://github.com/OCA/commission/pull/646/commits/c6a99353a7caf383350640a5ee28ca586cd14e46#diff-01f804f51f9fa191855019e02883f8d65c56f4cd2394fbf6687d6b211d0c2be5L17-R26).
* If you are using `toggle_active` method, change it to be explicit with `action_archive` or `action_unarchive` new methods. More info at [odoo/odoo#183691](https://github.com/odoo/odoo/pull/183691).
* You may consider add the new decorator `@api.private` to some methods with no initial underscore to make them not accessible to external API. More info at [odoo/odoo#195402](https://github.com/odoo/odoo/pull/195402).
* You may now use new dynamic dates parameters for domains. More info at [odoo/odoo#216665](https://github.com/odoo/odoo/pull/216665).
* When using `SUPERUSER_ID` variable, import it from `api` instead inside `odoo` itself. More info at [odoo/odoo@d6a955f10483](https://github.com/odoo/odoo/commit/d6a955f10483).
* Replace decorator `@ormcache_context` by the regular `@ormcache` and the context keys set as parameters with `self.env.context.get("key")`. More info at [odoo/odoo#220725](https://github.com/odoo/odoo/pull/220725).
* If using `urljoin` from `urllib.parse`, switch to `odoo.tools.urls.urljoin` helper which abstracts its usage and cover more cases. More info at [odoo/odoo@977e62d91f3e](https://github.com/odoo/odoo/commit/977e62d91f3e).
* You may want to use the new `odoo.domain` and `odoo.Domain` API for domain manipulation. See some examples at [odoo/odoo#170009](https://github.com/odoo/odoo/pull/170009).
* Replace the `args` parameter by `domain` in `name_search` overrides. More info at https://github.com/odoo/odoo/commit/e35bcedab20048807aa3aa17dd8d1e4ea932e3d5.
* Remove decorator `@api.returns`, and adapt any call relaying on the former behavior. More info at [odoo/odoo#182709](https://github.com/odoo/odoo/pull/182709).
* `Product Unit of Measure` has been renamed to `Product Unit`, so all the occurrences in `digits` attribute of the fields, or direct calls to `self.env['decimal.precision'].precision_get('Product Unit of Measure')` should be replaced with the new name. Beware that not changing this name won't provoke any error, but it will simply work with 2 decimals. More info at [odoo/odoo@8fd73ea390ba0](https://github.com/odoo/odoo/commit/8fd73ea390ba0de0a7ed418398ffdd6b8e8f55fd).
* Remove `string` and `expand` attributes from the `<group>` tags in search views, like done in [odoo/odoo#220023](https://github.com/odoo/odoo/pull/220023).
* Add tests to increase code coverage.
* Disable tracking by setting `tracking_disable` on the whole test env (eg: `cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))` ) or evaluate the use of `BaseCommon` as base test class if you need to setup company, currency, users and groups in a special way).
* If your tests rely on demo data, now they are not installed by default, as in fact, Odoo advises not to rely on them, so it's the occasion to create the data on the tests themselves.
* If you were using `odoo-test-helper` library for loading some fake model in the tests, now you can do it natively without the library.

  Before:

  ``` python
  from odoo_test_helper import FakeModelLoader

  @classmethod
  def setUpClass(cls):
      ...
      cls.loader = FakeModelLoader(cls.env, cls.__module__)
      cls.loader.backup_registry()
      from .fake_models import FakeModel
      cls.loader.update_registry((FakeModel,))

  @classmethod
  def tearDownClass(cls):
      cls.loader.restore_registry()
      ...
  ```

  Now:

  ```python
  from odoo.orm.model_classes import add_to_registry

  @classmethod
  def setUpClass(cls):
      ...
      from .fake_models import FakeModel
      add_to_registry(cls.registry, FakeModel)
      cls.registry._setup_models__(cls.env.cr, ["fake.model"])
      cls.registry.init_models(cls.env.cr, ["fake.model"], {"models_to_check": True})
      cls.addClassCleanup(cls.registry.__delitem__, "fake.model")
  ```

* Check tasks of previous versions if you are migrating from lower versions than 18. It's also recommended to check past migration guides for things not done in previous migrations.
* Do the rest of the changes you need to perform for making the module works on the new version.

# Tasks NOT to do in the migration

* change copyright year

  A line like this:

  ```
  # Copyright 2024 ACME Ltd - Johnny Glamour
  ```
  says "copyright FROM 2024". There's no need to change the year to the current one.

* change original authors

# How-to

## Technical method to migrate a module from "18.0" to "19.0" branch

* `$repo`: the OCA repository hosting the module
* `$module`: the name of the module you want to migrate
* `$user_org`: your GitHub login or organization name

**Full process**

* On a shell command:
  ```bash
  $ git clone https://github.com/OCA/$repo -b 19.0
  $ cd $repo
  $ git checkout -b 19.0-mig-$module origin/19.0
  $ git format-patch --keep-subject --stdout origin/19.0..origin/18.0 -- $module | git am -3 --keep
  $ pre-commit run -a  # to run pre-commit linters and formatters (please ignore pylint errors at this stage)
  $ git add -A
  $ git commit -m "[IMP] $module: pre-commit auto fixes"  --no-verify  # it is important to do all the formatting in one commit the first time
  ```
* On the last step, there may be no changes done by pre-commit, so just ignore the message saying "Nothing to commit".
* Check https://github.com/OCA/maintainer-tools/wiki/Merge-commits-in-pull-requests for a procedure for reducing commits from "OCA Transbot...".
* If the **module is renamed** in the migration, you have to rename the whole commit history. If not done, on the next version, when these commands will be executed again, only the latest commit will be brought. For doing the renaming, execute the following commands on older versions of git:
  ```
  git filter-branch --tree-filter 'if [ -d $module ]; then mv $module $new_module_name; fi' HEAD
  git rebase origin/19.0
  ```
  or this on newer ones:
  ```
  git filter-repo --path-rename $module/:$new_module_name/ --refs HEAD --force
  ```
* Adapt the module to the 19.0 version following [tasks to do](https://github.com/OCA/maintainer-tools/wiki/Migration-to-version-19.0#tasks-to-do-in-the-migration).
* On a shell command, type this for uploading the content to GitHub:
  ```bash
  $ git add --all
  $ git commit -m "[MIG] $module: Migration to 19.0"
  $ git remote add $user_org git@github.com:$user_org/$repo.git # This mode requires an SSH key in the GitHub account
  $ ... or ....
  $ git remote add $user_org https://github.com/$user_org/$repo.git # This will required to enter user/password each time
  $ git push $user_org 19.0-mig-$module --set-upstream
  ```
* Follow the link on the command line or check in https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork how to create the pull request.
* For being easily searchable and avoiding to duplicate efforts, please name the pull request following this pattern: `[19.0][MIG] <module>: Migration to 19.0`.

**Troubleshooting**

Sometimes, when performing these operations, the process can hang due to conflicts on the patches being applied. One of the possible problems is because a patch removes entirely a file and `git am` is not able to resolve this. It ends with a message `error: ...: patch does not apply`.

If that's your case, you can add `--ignore-whitespace` at the end of the `git am` command for allowing the patch to be applied, although there will be still conflicts to be solved, but they will be doable through standard conflict resolution system. Starting from the previous situation, you will need to do:

```bash
git am --abort
git format-patch --keep-subject --stdout origin/19.0..origin/18.0 -- <module path> | git am -3 --keep --ignore-whitespace
# resolve conflicts (for example git rm <file>)
git add --all
git am --continue
```
