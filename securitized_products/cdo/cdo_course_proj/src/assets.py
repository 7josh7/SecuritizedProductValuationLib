"""
assets.py

Asset definitions and helper functions for the CDO collateral pool.

The classes in this file describe reusable asset behavior. Course-project
assumptions are kept in factory functions so the model can later load different
inputs from a README, CSV, database, or user interface without changing the
class definitions.
"""

from abc import ABC, abstractmethod


def periodic_coupon(face_value: float, annual_coupon_rate: float, payments_per_year: int) -> float:
    """
    Coupon paid each period.
    """
    return face_value * annual_coupon_rate / payments_per_year


def periodic_default_probability(annual_default_prob: float, payments_per_year: int) -> float:
    """
    Convert annual default probability into periodic default probability.

    This respects compounding:
    q = 1 - (1 - annual_default_prob) ** (1 / payments_per_year)
    """
    return 1.0 - (1.0 - annual_default_prob) ** (1.0 / payments_per_year)


def recovery_rate_from_lgd(lgd: float) -> float:
    """
    Recovery rate implied by loss-given-default.
    """
    return 1.0 - lgd


def recovery_amount(face_value: float, lgd: float) -> float:
    """
    Dollar recovery if the asset defaults.
    """
    return face_value * recovery_rate_from_lgd(lgd)


def loss_amount(face_value: float, lgd: float) -> float:
    """
    Dollar loss if the asset defaults.
    """
    return face_value * lgd


class Asset(ABC):
    """
    Parent class for assets that can be included in a CDO collateral pool.

    The parent class defines the common interface expected by later portfolio,
    simulation, and waterfall code. Subclasses decide how coupons, defaults,
    recoveries, and principal should be calculated.
    """

    def __init__(self, name: str, face_value: float, maturity_years: int) -> None:
        self.name = name
        self.face_value = face_value
        self.maturity_years = maturity_years

    @property
    @abstractmethod
    def num_periods(self) -> int:
        """
        Number of payment periods over the asset life.
        """

    @property
    @abstractmethod
    def coupon_per_period(self) -> float:
        """
        Coupon paid each period if the asset has not defaulted.
        """

    @property
    @abstractmethod
    def default_prob_per_period(self) -> float:
        """
        Default probability for one payment period.
        """

    @property
    @abstractmethod
    def recovery_amount(self) -> float:
        """
        Dollar recovery if the asset defaults.
        """

    @property
    @abstractmethod
    def loss_amount(self) -> float:
        """
        Dollar loss if the asset defaults.
        """

    @abstractmethod
    def summary(self) -> dict:
        """
        Return the asset's assumptions and key calculated values.
        """


class CorporateBond(Asset):
    """
    Fixed-coupon corporate bond used as CDO collateral.

    This class does not hard-code course assumptions. It receives assumptions
    from the caller and provides reusable calculations for coupon, default,
    recovery, and loss amounts.
    """

    def __init__(
        self,
        name: str,
        face_value: float,
        annual_coupon_rate: float,
        annual_default_prob: float,
        lgd: float,
        maturity_years: int,
        payments_per_year: int,
        market_ytm: float | None = None,
        risk_free_rate: float | None = None,
    ) -> None:
        super().__init__(name=name, face_value=face_value, maturity_years=maturity_years)
        self.annual_coupon_rate = annual_coupon_rate
        self.annual_default_prob = annual_default_prob
        self.lgd = lgd
        self.payments_per_year = payments_per_year
        self.market_ytm = market_ytm
        self.risk_free_rate = risk_free_rate

    @property
    def recovery_rate(self) -> float:
        return recovery_rate_from_lgd(self.lgd)

    @property
    def num_periods(self) -> int:
        return self.maturity_years * self.payments_per_year

    @property
    def coupon_per_period(self) -> float:
        return periodic_coupon(
            face_value=self.face_value,
            annual_coupon_rate=self.annual_coupon_rate,
            payments_per_year=self.payments_per_year,
        )

    @property
    def default_prob_per_period(self) -> float:
        return periodic_default_probability(
            annual_default_prob=self.annual_default_prob,
            payments_per_year=self.payments_per_year,
        )

    @property
    def recovery_amount(self) -> float:
        return recovery_amount(face_value=self.face_value, lgd=self.lgd)

    @property
    def loss_amount(self) -> float:
        return loss_amount(face_value=self.face_value, lgd=self.lgd)

    def summary(self) -> dict:
        return {
            "name": self.name,
            "asset_type": self.__class__.__name__,
            "face_value": self.face_value,
            "annual_coupon_rate": self.annual_coupon_rate,
            "coupon_per_period": self.coupon_per_period,
            "annual_default_prob": self.annual_default_prob,
            "default_prob_per_period": self.default_prob_per_period,
            "lgd": self.lgd,
            "recovery_rate": self.recovery_rate,
            "recovery_amount": self.recovery_amount,
            "loss_amount": self.loss_amount,
            "maturity_years": self.maturity_years,
            "num_periods": self.num_periods,
            "payments_per_year": self.payments_per_year,
            "market_ytm": self.market_ytm,
            "risk_free_rate": self.risk_free_rate,
        }


def create_corporate_bond_pool(
    number_of_bonds: int,
    face_value: float,
    annual_coupon_rate: float,
    annual_default_prob: float,
    lgd: float,
    maturity_years: int,
    payments_per_year: int,
    market_ytm: float | None = None,
    risk_free_rate: float | None = None,
    name_prefix: str = "Bond",
) -> list[CorporateBond]:
    """
    Create a homogeneous corporate-bond pool from caller-provided assumptions.
    """
    bonds = []

    for i in range(number_of_bonds):
        bonds.append(
            CorporateBond(
                name=f"{name_prefix}_{i + 1}",
                face_value=face_value,
                annual_coupon_rate=annual_coupon_rate,
                annual_default_prob=annual_default_prob,
                lgd=lgd,
                maturity_years=maturity_years,
                payments_per_year=payments_per_year,
                market_ytm=market_ytm,
                risk_free_rate=risk_free_rate,
            )
        )

    return bonds


def create_course_project_bonds() -> list[CorporateBond]:
    """
    Create the 10 corporate bonds from the CDO course project.

    Course assumptions live here, not inside CorporateBond:
    - 10 bonds
    - $10MM face value each
    - 6% annual coupon rate
    - 4% annual default probability
    - 60% LGD
    - 5-year maturity
    - quarterly payments
    - 9% market YTM
    - 1% risk-free rate
    """
    return create_corporate_bond_pool(
        number_of_bonds=10,
        face_value=10_000_000,
        annual_coupon_rate=0.06,
        annual_default_prob=0.04,
        lgd=0.60,
        maturity_years=5,
        payments_per_year=4,
        market_ytm=0.09,
        risk_free_rate=0.01,
    )
