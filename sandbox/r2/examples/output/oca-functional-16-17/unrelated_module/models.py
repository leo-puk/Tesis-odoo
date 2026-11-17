from odoo import fields, models
class Unrelated(models.Model):
    _name = 'functional.unrelated'
    name = fields.Char()
