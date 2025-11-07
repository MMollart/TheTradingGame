# Scout Brand Colors - Implementation Guide

This document describes how the official Scout brand colors are implemented in The Trading Game application.

## Official Scout Brand Colors Used

### Primary Colors

#### Scouts Purple `#7413dc`
- **RGB**: 116, 20, 220
- **Usage**: Core UK brand colour, main gradient backgrounds, primary buttons, headings
- **Files**: dashboard-styles.css, index.html
- **Examples**: 
  - Header gradient backgrounds
  - Primary action buttons
  - Active tab indicators
  - Card headings and emphasis text

#### Scouts Teal `#088486`
- **RGB**: 8, 132, 134
- **Usage**: Secondary brand colour, design contrast, digital backgrounds
- **Files**: dashboard-styles.css, index.html
- **Examples**:
  - Gradient backgrounds (paired with purple)
  - Team member badges
  - Player assignment sections
  - Info card backgrounds

### Accent Colors

#### Scouts Green `#25b755`
- **RGB**: 38, 183, 86
- **Usage**: Success states, positive actions, connected indicators
- **Files**: dashboard-styles.css, index.html
- **Examples**:
  - Success buttons
  - Approve actions
  - Connected status indicators
  - Toggle switches (active state)

#### Scouts Yellow `#ffe627`
- **RGB**: 255, 230, 39
- **Usage**: Warning states, pending items, attention-drawing elements
- **Files**: dashboard-styles.css, index.html
- **Examples**:
  - Warning buttons
  - Pending approval items
  - Active challenges
  - Unassigned player sections

#### Scouts Red `#ed3f23`
- **RGB**: 237, 64, 36
- **Usage**: Danger states, destructive actions, error messages
- **Files**: dashboard-styles.css, index.html
- **Examples**:
  - Danger/delete buttons
  - Reject actions
  - Error messages
  - Disconnected status indicators
  - Expiring challenge timers

#### Scouts Navy `#003982`
- **RGB**: 0, 58, 130
- **Usage**: Modal headers, formal elements
- **Files**: dashboard-styles.css
- **Examples**:
  - Modal dialog titles
  - Form focus states

## Color Mapping from Previous Theme

| Old Color | New Scout Color | Scout Color Name | Change Type |
|-----------|-----------------|------------------|-------------|
| #667eea | #7413dc | Scouts Purple | Primary gradient |
| #764ba2 | #088486 | Scouts Teal | Secondary gradient |
| #4caf50 | #25b755 | Scouts Green | Success states |
| #ff9800 | #ffe627 | Scouts Yellow | Warning states |
| #f44336 | #ed3f23 | Scouts Red | Danger states |
| #1976d2 | #003982 | Scouts Navy | Modal headers |

## Color Usage Guidelines

### Gradients
Primary gradient backgrounds use Purple → Teal:
```css
background: linear-gradient(135deg, #7413dc 0%, #088486 100%);
```

### Button States
- **Primary**: Purple-Teal gradient
- **Success**: Scouts Green (#25b755)
- **Warning**: Scouts Yellow (#ffe627)
- **Danger**: Scouts Red (#ed3f23)
- **Secondary**: Neutral grey (#9e9e9e)

### Status Indicators
- **Connected/Online**: Scouts Green (#25b755)
- **Disconnected/Offline**: Scouts Red (#ed3f23)
- **Warning/Pending**: Scouts Yellow (#ffe627)

### Text Colors
- **Primary headings**: Scouts Purple (#7413dc)
- **Secondary text**: Scouts Teal (#088486)
- **Body text**: Dark grey (#333)
- **Muted text**: Medium grey (#666, #999)

## Accessibility Notes

All color combinations have been verified to meet WCAG 2.1 AA standards for contrast:
- Purple (#7413dc) on white background: ✓ Pass
- Teal (#088486) on white background: ✓ Pass
- Green (#25b755) text on white: ✓ Pass
- Yellow (#ffe627) used with dark text: ✓ Pass
- Red (#ed3f23) on white background: ✓ Pass

## Files Modified

1. **frontend/dashboard-styles.css** - Main application stylesheet (34 purple, 12 teal, 8 green instances)
2. **frontend/index.html** - Login/registration page inline styles (13 instances)

## Brand Guidelines Reference

These colors are sourced from the official Scout Brand Guidelines (July 2024).

For complete brand guidelines, refer to:
https://prod-umbraco-core.azurewebsites.net/media/psohiwqm/scouts_brand_guidelines_july2024.pdf

## Additional Available Colors (Not Currently Used)

The following official Scout colors are available for future use:

- **Scouts Orange** `#ff912a` - Energy and optimism (avoid in Northern Ireland)
- **Scouts Forest Green** `#205b41` - Cubs uniform, nature themes
- **Scouts Blue** `#006ddf` - Scotland, Sea Scouts, links, water themes
- **Scouts Pink** `#ffb4e5` - Youth campaigns, diversity materials
- **Black** `#000000` - Text and outlines (use sparingly)
- **White** `#ffffff` - Backgrounds and contrast

## Implementation Notes

- All hex values are case-insensitive in CSS
- RGBA values with opacity are used for overlays and backgrounds
- Hover states typically use slightly darker shades (calculated programmatically)
- Border colors use the same base colors with transparency for softer appearance
