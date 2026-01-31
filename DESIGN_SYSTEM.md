# Design System Integration

## Overview
This document describes the design system integrated into the Polaremail email templates, based on GitHub's dark theme aesthetic.

## Color Palette

### Primary Colors
- `#0d1117` - Main background (GitHub dark)
- `#161b22` - Card backgrounds
- `#21262d` - Nested elements, borders

### Text Colors
- `#e6edf3` - Main text (primary)
- `#8b949e` - Secondary/muted text
- `#6e7681` - Timestamps, labels (tertiary)

### Accent Colors
- `#58a6ff` - Links, primary actions (blue)
- `#3fb950` - Positive/good status (green)
- `#d29922` - Warning/caution (yellow)
- `#f85149` - Alert/danger (red)
- `#a371f7` - Special highlights (purple)

### Status Colors (for gauges and indicators)
- `#238636` - Optimal zone (green)
- `#3fb950` - Good status (light green)
- `#d29922` - Caution (yellow/orange)
- `#f85149` - Warning (red)
- `#8b949e` - Neutral (gray)

### Chart Colors
- `#58a6ff` - CTL (Fitness) - Blue
- `#f85149` - ATL (Fatigue) - Red
- `#d29922` - TSB (Form) - Yellow
- `#a371f7` - HRV - Purple
- `#3fb950` - Sleep - Green

## Typography

### Font Stack
System fonts for maximum email compatibility:
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
```

### Font Sizes
- Extra small: 11px
- Small: 12px
- Base: 14px
- Large: 16px
- Extra large: 20px
- 2X large: 24px
- 3X large: 32px

### Font Weights
- Normal: 400
- Medium: 500
- Semibold: 600
- Bold: 700

## Spacing System
- 4px (space-1)
- 8px (space-2)
- 12px (space-3)
- 16px (space-4)
- 20px (space-5)
- 24px (space-6)
- 32px (space-8)
- 40px (space-10)
- 48px (space-12)

## Layout Structure

### Health Digest Email Layout
1. **Header** - Logo/title, week date range, quick status
2. **Hero Metrics** - 4 cards (ACWR, HRV Status, Form, Alerts)
3. **Training Load Section** - Weekly stats, ACWR, Monotony & Strain
4. **Recovery Status Section** - HRV Quadrant visualization
5. **Sleep Analysis** - Sleep architecture, sleep debt
6. **Alerts Section** - Conditional warnings
7. **Performance Management Chart** - CTL/ATL/TSB visualization
8. **Conditions & Optimization** - Time-of-day insights
9. **Insight of the Week** - AI-generated personalized insight
10. **Footer** - Data period, settings link

### Basic Training Report Layout
1. **Header** - Title, date range, overall rating
2. **Training Summary** - Sessions, duration, distance, calories
3. **Heart Rate Zones** - Zone distribution with bars
4. **Recovery & Sleep** - Recharge, HRV, sleep metrics
5. **Week Highlights** - Achievements and concerns
6. **Sports Breakdown** - Per-sport statistics
7. **Training Load** - Cardio and muscle load
8. **Footer** - Generation info, links

## Email Compatibility
All styles are inline for maximum email client compatibility. The design uses:
- Table-based layouts for email client compatibility
- Inline CSS styles
- No external stylesheets
- Fallback fonts for older email clients
- Mobile-responsive design with appropriate breakpoints

## Usage Examples

### Status Color Application
```html
<!-- Optimal status -->
<span style="color: #3fb950;">Optimal</span>

<!-- Caution status -->
<span style="color: #d29922;">Caution</span>

<!-- Danger status -->
<span style="color: #f85149;">Danger</span>
```

### Card Background
```html
<table style="background-color: #21262d; border-radius: 8px; border: 1px solid #21262d;">
```

### Text Hierarchy
```html
<!-- Primary text -->
<h2 style="color: #e6edf3; font-size: 16px; font-weight: 600;">Section Title</h2>

<!-- Secondary text -->
<span style="color: #8b949e; font-size: 14px;">Description text</span>

<!-- Tertiary text -->
<span style="color: #6e7681; font-size: 12px;">Label or timestamp</span>
```
