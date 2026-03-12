
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import declared_attr


class TenantMixin:
    """
    Mixin to enforce company ownership on models.
    Any model inheriting this automatically gets company_id.
    """

    @declared_attr
    def company_id(cls):
        return Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)