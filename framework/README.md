# MatchEng Framework

This directory contains the core framework components for the MatchEng application.

## Structure

```
framework/
├── __init__.py          # Framework exports
├── response.py          # Standardized API response classes
├── exceptions.py        # Custom exception classes
└── README.md           # This file
```

## Components

### APIResponse Classes

Standardized response classes for consistent API responses across the application.

#### Usage

```python
from framework import SuccessResponse, ErrorResponse

# Success response
return SuccessResponse(
    data={"result": "success"},
    message="Operation completed",
    status_code=200
).to_json()

# Error response
return ErrorResponse(
    error="Validation failed",
    status_code=400,
    details={"field": "email", "issue": "Invalid format"}
).to_json()
```

### Exception Classes

Custom exceptions for better error handling.

#### Usage

```python
from framework import ValidationError, ProcessingError

# Raise validation error
if not email:
    raise ValidationError("Email is required")

# Raise processing error
if processing_failed:
    raise ProcessingError("Failed to process file")
```

## UI Components

The framework also includes standardized UI components in `/static/ui-components.js`:

- `showToast(message, type, duration)` - Display toast notifications
- `setStatus(elementId, message, type)` - Set status messages
- `createCard(title, content, options)` - Create standardized cards
- `createStatCard(label, value, subtitle)` - Create stat cards
- `createProgressBar(percent, text)` - Create progress bars
- `createActionCard(...)` - Create action cards with CTAs
- `formatNumber(num)` - Format numbers with locale
- `formatDate(date)` - Format dates
- `escapeHtml(text)` - Escape HTML to prevent XSS

## CSS Components

Standardized CSS classes are available in `/static/stylesheets.css`:

- `.page-header` - Standardized page headers
- `.card` - Standardized card containers
- `.action-card` - Action cards with CTAs
- `.status` - Status message containers
- `.progress-bar` - Progress indicators
- `.stats-grid` - Grid layout for statistics
- `.form-actions` - Form action button containers

## Workflow Integration

The framework supports the complete workflow:

1. **Upload** → Upload CSV files
2. **Analytics** → View file analytics and data quality
3. **Process** → Run matching engine (can continue from Analytics)
4. **Results** → View and download matching results

### Continuing from Analytics to Matching

Users can now seamlessly continue from the Analytics page to the Matching process:

1. View analytics for a processed file
2. Click "Run Matching Engine" button
3. Automatically navigate to Process page with file pre-selected
4. Run matching with standardized columns

## Best Practices

1. **Use standardized responses**: Always use `SuccessResponse` or `ErrorResponse` for API endpoints
2. **Consistent UI**: Use standardized CSS classes and UI component functions
3. **Error handling**: Use custom exceptions for better error messages
4. **Security**: Always use `escapeHtml()` when rendering user content

