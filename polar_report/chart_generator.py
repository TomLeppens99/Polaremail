"""
Chart generation for Health Digest emails.

Uses QuickChart.io for email-safe chart rendering (no JavaScript/SVG required).
All charts are rendered as PNG images via URL.
"""

import json
import urllib.parse
from typing import List, Dict, Optional


class ChartGenerator:
    """
    Generate chart URLs using QuickChart.io API.
    Charts are rendered server-side as PNG images, safe for email.
    """

    BASE_URL = "https://quickchart.io/chart"
    DEFAULT_WIDTH = 500
    DEFAULT_HEIGHT = 200

    # Color scheme
    COLORS = {
        "primary": "#e63946",
        "secondary": "#457b9d",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#17a2b8",
        "light": "#f8f9fa",
        "dark": "#343a40",
        "fitness": "#4285f4",  # Blue for CTL
        "fatigue": "#ea4335",  # Red for ATL
        "form": "#fbbc04",     # Yellow for TSB
        "zone1": "#90cdf4",    # Recovery
        "zone2": "#68d391",    # Light
        "zone3": "#faf089",    # Moderate
        "zone4": "#feb2b2",    # Hard
        "zone5": "#e63946",    # Maximum
    }

    # ACWR zones
    ACWR_ZONES = {
        "undertrained": {"color": "#6c757d", "range": (0, 0.8)},
        "optimal": {"color": "#28a745", "range": (0.8, 1.3)},
        "caution": {"color": "#ffc107", "range": (1.3, 1.5)},
        "danger": {"color": "#dc3545", "range": (1.5, 2.0)},
    }

    def __init__(self, width: int = None, height: int = None):
        """
        Initialize chart generator.

        Args:
            width: Default chart width in pixels
            height: Default chart height in pixels
        """
        self.width = width or self.DEFAULT_WIDTH
        self.height = height or self.DEFAULT_HEIGHT

    def _generate_url(
        self,
        chart_config: Dict,
        width: int = None,
        height: int = None
    ) -> str:
        """
        Generate QuickChart URL from chart configuration.

        Args:
            chart_config: Chart.js configuration dictionary
            width: Chart width (overrides default)
            height: Chart height (overrides default)

        Returns:
            URL string for the chart image
        """
        config_json = json.dumps(chart_config, separators=(',', ':'))
        encoded = urllib.parse.quote(config_json, safe='')

        w = width or self.width
        h = height or self.height

        return f"{self.BASE_URL}?c={encoded}&w={w}&h={h}"

    def generate_acwr_gauge(
        self,
        acwr_value: float,
        status: str
    ) -> str:
        """
        Generate ACWR gauge chart.

        Args:
            acwr_value: ACWR value (e.g., 1.15)
            status: Status string ("undertrained", "optimal", "caution", "danger")

        Returns:
            URL for gauge chart image
        """
        # Determine color based on status
        colors = {
            "undertrained": self.COLORS["light"],
            "optimal": self.COLORS["success"],
            "caution": self.COLORS["warning"],
            "danger": self.COLORS["danger"]
        }
        color = colors.get(status, self.COLORS["primary"])

        # Create a radial gauge using doughnut chart
        chart_config = {
            "type": "doughnut",
            "data": {
                "datasets": [{
                    "data": [acwr_value, max(0, 2 - acwr_value)],
                    "backgroundColor": [color, "#e9ecef"],
                    "borderWidth": 0
                }]
            },
            "options": {
                "circumference": 180,
                "rotation": 270,
                "cutoutPercentage": 70,
                "plugins": {
                    "datalabels": {
                        "display": True,
                        "font": {"size": 24, "weight": "bold"},
                        "color": color
                    }
                },
                "legend": {"display": False}
            }
        }

        return self._generate_url(chart_config, width=200, height=120)

    def generate_pmc_chart(
        self,
        dates: List[str],
        ctl_series: List[float],
        atl_series: List[float],
        tsb_series: List[float]
    ) -> str:
        """
        Generate Performance Management Chart (CTL/ATL/TSB).

        Args:
            dates: List of date labels
            ctl_series: Chronic Training Load values
            atl_series: Acute Training Load values
            tsb_series: Training Stress Balance values

        Returns:
            URL for PMC chart image
        """
        chart_config = {
            "type": "line",
            "data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": "Fitness (CTL)",
                        "data": ctl_series,
                        "borderColor": self.COLORS["fitness"],
                        "backgroundColor": "transparent",
                        "borderWidth": 2,
                        "pointRadius": 0,
                        "tension": 0.3
                    },
                    {
                        "label": "Fatigue (ATL)",
                        "data": atl_series,
                        "borderColor": self.COLORS["fatigue"],
                        "backgroundColor": "transparent",
                        "borderWidth": 2,
                        "pointRadius": 0,
                        "tension": 0.3
                    },
                    {
                        "label": "Form (TSB)",
                        "data": tsb_series,
                        "borderColor": self.COLORS["form"],
                        "backgroundColor": "rgba(251, 188, 4, 0.1)",
                        "borderWidth": 2,
                        "pointRadius": 0,
                        "fill": True,
                        "tension": 0.3
                    }
                ]
            },
            "options": {
                "scales": {
                    "yAxes": [{
                        "gridLines": {"color": "#eee"},
                        "ticks": {"fontSize": 10}
                    }],
                    "xAxes": [{
                        "gridLines": {"display": False},
                        "ticks": {"fontSize": 10, "maxTicksLimit": 8}
                    }]
                },
                "legend": {
                    "position": "bottom",
                    "labels": {"fontSize": 10}
                }
            }
        }

        return self._generate_url(chart_config, width=500, height=250)

    def generate_hrv_sparkline(
        self,
        hrv_values: List[float],
        baseline_mean: float = None
    ) -> str:
        """
        Generate HRV trend sparkline.

        Args:
            hrv_values: List of HRV values
            baseline_mean: Optional baseline mean to show as reference line

        Returns:
            URL for sparkline chart image
        """
        datasets = [{
            "data": hrv_values,
            "borderColor": self.COLORS["primary"],
            "backgroundColor": "rgba(230, 57, 70, 0.1)",
            "borderWidth": 2,
            "pointRadius": 3,
            "fill": True,
            "tension": 0.3
        }]

        # Add baseline reference line if provided
        if baseline_mean:
            datasets.append({
                "data": [baseline_mean] * len(hrv_values),
                "borderColor": "#999",
                "borderDash": [5, 5],
                "borderWidth": 1,
                "pointRadius": 0,
                "fill": False
            })

        chart_config = {
            "type": "line",
            "data": {
                "labels": [f"Day {i+1}" for i in range(len(hrv_values))],
                "datasets": datasets
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "yAxes": [{"gridLines": {"display": False}, "ticks": {"display": False}}],
                    "xAxes": [{"gridLines": {"display": False}, "ticks": {"display": False}}]
                }
            }
        }

        return self._generate_url(chart_config, width=200, height=60)

    def generate_hrv_quadrant(
        self,
        current_mean: float,
        current_cv: float,
        quadrant: str
    ) -> str:
        """
        Generate HRV quadrant visualization.

        Args:
            current_mean: Current HRV mean
            current_cv: Current HRV CV (coefficient of variation)
            quadrant: Current quadrant classification

        Returns:
            URL for quadrant chart image
        """
        # Quadrant colors
        quadrant_colors = {
            "coping_well": self.COLORS["success"],
            "adapting": self.COLORS["info"],
            "fatigued": self.COLORS["warning"],
            "maladaptation": self.COLORS["danger"]
        }

        color = quadrant_colors.get(quadrant, self.COLORS["primary"])

        chart_config = {
            "type": "scatter",
            "data": {
                "datasets": [{
                    "data": [{"x": current_cv, "y": current_mean}],
                    "backgroundColor": color,
                    "pointRadius": 12,
                    "pointStyle": "circle"
                }]
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "xAxes": [{
                        "scaleLabel": {"display": True, "labelString": "CV %"},
                        "ticks": {"min": 0, "max": 30}
                    }],
                    "yAxes": [{
                        "scaleLabel": {"display": True, "labelString": "HRV (ms)"},
                        "ticks": {"min": 20, "max": 80}
                    }]
                }
            }
        }

        return self._generate_url(chart_config, width=200, height=200)

    def generate_sleep_composition_bar(
        self,
        deep_percent: float,
        rem_percent: float,
        light_percent: float
    ) -> str:
        """
        Generate stacked bar chart for sleep composition.

        Args:
            deep_percent: Deep sleep percentage
            rem_percent: REM sleep percentage
            light_percent: Light sleep percentage

        Returns:
            URL for stacked bar chart image
        """
        chart_config = {
            "type": "horizontalBar",
            "data": {
                "labels": ["Sleep"],
                "datasets": [
                    {
                        "label": "Deep",
                        "data": [deep_percent],
                        "backgroundColor": "#4e79a7"
                    },
                    {
                        "label": "REM",
                        "data": [rem_percent],
                        "backgroundColor": "#f28e2c"
                    },
                    {
                        "label": "Light",
                        "data": [light_percent],
                        "backgroundColor": "#76b7b2"
                    }
                ]
            },
            "options": {
                "indexAxis": "y",
                "scales": {
                    "xAxes": [{
                        "stacked": True,
                        "ticks": {"min": 0, "max": 100}
                    }],
                    "yAxes": [{
                        "stacked": True,
                        "display": False
                    }]
                },
                "legend": {
                    "position": "bottom",
                    "labels": {"fontSize": 10}
                }
            }
        }

        return self._generate_url(chart_config, width=300, height=80)

    def generate_time_of_day_bar(
        self,
        performance_by_slot: Dict[str, Dict]
    ) -> str:
        """
        Generate bar chart for time-of-day performance.

        Args:
            performance_by_slot: Dict with slot names and relative performance

        Returns:
            URL for bar chart image
        """
        slots = list(performance_by_slot.keys())
        values = [performance_by_slot[s].get("relative_performance", 0) for s in slots]

        # Color bars based on performance (green for best, red for worst)
        colors = []
        for v in values:
            if v <= 0:
                colors.append(self.COLORS["success"])
            elif v < 3:
                colors.append(self.COLORS["info"])
            elif v < 5:
                colors.append(self.COLORS["warning"])
            else:
                colors.append(self.COLORS["danger"])

        chart_config = {
            "type": "bar",
            "data": {
                "labels": [s.replace("_", " ").title() for s in slots],
                "datasets": [{
                    "label": "Performance vs Best (%)",
                    "data": values,
                    "backgroundColor": colors
                }]
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "yAxes": [{
                        "scaleLabel": {"display": True, "labelString": "% vs Best"},
                        "ticks": {"fontSize": 10}
                    }],
                    "xAxes": [{
                        "ticks": {"fontSize": 9}
                    }]
                }
            }
        }

        return self._generate_url(chart_config, width=400, height=180)

    def generate_training_load_trend(
        self,
        daily_loads: List[float],
        days: int = 7
    ) -> str:
        """
        Generate training load trend chart.

        Args:
            daily_loads: List of daily training loads
            days: Number of days to show

        Returns:
            URL for trend chart image
        """
        loads = daily_loads[-days:] if len(daily_loads) > days else daily_loads
        labels = [f"Day {i+1}" for i in range(len(loads))]

        chart_config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Training Load",
                    "data": loads,
                    "backgroundColor": self.COLORS["primary"],
                    "borderRadius": 4
                }]
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "yAxes": [{
                        "ticks": {"beginAtZero": True, "fontSize": 10}
                    }],
                    "xAxes": [{
                        "ticks": {"fontSize": 10}
                    }]
                }
            }
        }

        return self._generate_url(chart_config, width=300, height=150)

    def generate_sleep_debt_chart(
        self,
        debt_hours: float,
        max_debt: float = 10
    ) -> str:
        """
        Generate sleep debt indicator chart.

        Args:
            debt_hours: Current sleep debt in hours
            max_debt: Maximum scale for chart

        Returns:
            URL for chart image
        """
        # Determine color based on debt severity
        if debt_hours <= 0:
            color = self.COLORS["success"]
        elif debt_hours < 3:
            color = self.COLORS["info"]
        elif debt_hours <= 7:
            color = self.COLORS["warning"]
        else:
            color = self.COLORS["danger"]

        chart_config = {
            "type": "doughnut",
            "data": {
                "datasets": [{
                    "data": [min(debt_hours, max_debt), max(0, max_debt - debt_hours)],
                    "backgroundColor": [color, "#e9ecef"],
                    "borderWidth": 0
                }]
            },
            "options": {
                "cutoutPercentage": 70,
                "legend": {"display": False}
            }
        }

        return self._generate_url(chart_config, width=120, height=120)

    def generate_weather_scatter(
        self,
        performance_by_temp: Dict[str, float]
    ) -> str:
        """
        Generate weather vs performance scatter plot.

        Args:
            performance_by_temp: Dict mapping temp bands to efficiency values

        Returns:
            URL for scatter chart image
        """
        # Convert to scatter data points
        temp_values = {
            "cold": 5,
            "cool": 12.5,
            "moderate": 17.5,
            "warm": 22.5,
            "hot": 30
        }

        data_points = []
        for band, efficiency in performance_by_temp.items():
            if band in temp_values:
                data_points.append({
                    "x": temp_values[band],
                    "y": efficiency
                })

        if not data_points:
            return ""

        chart_config = {
            "type": "scatter",
            "data": {
                "datasets": [{
                    "data": data_points,
                    "backgroundColor": self.COLORS["primary"],
                    "pointRadius": 8
                }]
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "xAxes": [{
                        "scaleLabel": {"display": True, "labelString": "Temperature (°C)"},
                        "ticks": {"min": 0, "max": 35}
                    }],
                    "yAxes": [{
                        "scaleLabel": {"display": True, "labelString": "Efficiency"}
                    }]
                }
            }
        }

        return self._generate_url(chart_config, width=300, height=200)


# Convenience function for generating all charts for a digest
def generate_digest_charts(digest_report) -> Dict[str, str]:
    """
    Generate all chart URLs for a Health Digest report.

    Args:
        digest_report: HealthDigestReport object

    Returns:
        Dictionary mapping chart names to URLs
    """
    generator = ChartGenerator()
    charts = {}

    # ACWR Gauge
    if digest_report.acwr:
        charts["acwr_gauge"] = generator.generate_acwr_gauge(
            digest_report.acwr.acwr,
            digest_report.acwr.status
        )
        charts["training_load_trend"] = generator.generate_training_load_trend(
            digest_report.acwr.daily_loads_7_days
        )

    # HRV Charts
    if digest_report.hrv_quadrant:
        charts["hrv_sparkline"] = generator.generate_hrv_sparkline(
            digest_report.hrv_quadrant.trend_7_day,
            digest_report.hrv_quadrant.baseline_mean
        )
        charts["hrv_quadrant"] = generator.generate_hrv_quadrant(
            digest_report.hrv_quadrant.current_mean,
            digest_report.hrv_quadrant.current_cv,
            digest_report.hrv_quadrant.quadrant
        )

    # Sleep Charts
    if digest_report.sleep_architecture:
        comp = digest_report.sleep_architecture.composition
        charts["sleep_composition"] = generator.generate_sleep_composition_bar(
            comp.get("deep_percent", 0),
            comp.get("rem_percent", 0),
            comp.get("light_percent", 0)
        )

    if digest_report.sleep_debt:
        charts["sleep_debt"] = generator.generate_sleep_debt_chart(
            digest_report.sleep_debt.recent_debt_hours
        )

    # PMC Chart
    if digest_report.performance_management and digest_report.performance_management.series:
        series = digest_report.performance_management.series
        dates = [f"D{i+1}" for i in range(len(series.get("ctl", [])))]
        charts["pmc_chart"] = generator.generate_pmc_chart(
            dates[-42:],  # Last 42 days (6 weeks of daily data)
            series.get("ctl", [])[-42:],
            series.get("atl", [])[-42:],
            series.get("tsb", [])[-42:]
        )

    # Time of Day Chart
    if digest_report.time_of_day and digest_report.time_of_day.performance_by_slot:
        charts["time_of_day"] = generator.generate_time_of_day_bar(
            digest_report.time_of_day.performance_by_slot
        )

    return charts
