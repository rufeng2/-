# Frontend Workspace Refresh Design

## Goal

Refresh the existing Vue and Element Plus interface into a quiet, professional enterprise knowledge workspace without changing backend contracts or removing current workflows.

## Visual Direction

Use a neutral white and cool-gray foundation with graphite navigation, blue primary actions, and green status indicators. Avoid gradients, oversized headings, decorative cards, excessive rounding, and a single-hue palette. Typography remains system-native for fast Chinese rendering. Borders and spacing create hierarchy instead of shadows.

## Application Shell

The global sidebar remains resizable and collapsible. It receives a stronger product identity, clearer active navigation, stable icon-button dimensions, and a compact account area. Desktop pages occupy the full remaining viewport. Mobile uses a fixed top bar and drawer-style navigation with an overlay.

## Chat Workspace

Chat is organized into a narrow conversation rail and a flexible answer workspace. The duplicate account/logout footer is removed because account controls belong to the global shell. Conversation rows have stable action placement and clearer active state. Empty chat presents concise suggested question buttons rather than explanatory marketing content.

Messages use unframed rows with compact avatars; only user messages use a restrained filled bubble. Assistant answers prioritize long-form readability and source inspection. References use compact bordered rows with document, page, and preview information. The composer is fixed to the bottom of the chat workspace with knowledge-base selection and attachment/debug tools in a secondary toolbar. Send, stop, copy, regenerate, and feedback actions use Element Plus icons and tooltips.

## Operational Pages

Documents, evaluation, and administration use consistent page headers, dense toolbars, tables, status chips, pagination, dialogs, and empty/loading/error states. Page sections remain unframed. Cards are reserved for repeated metrics or individual items and use a maximum eight-pixel radius.

## Login

The login screen uses a centered, compact authentication panel with the product name visible in the first viewport. It avoids a marketing hero and keeps credentials, validation, and error feedback as the primary experience.

## Responsive And Accessibility

Desktop supports 1280 pixels and wider without wasted whitespace. Tablet and mobile collapse conversation navigation and stack toolbar controls without overlapping. Interactive controls retain visible focus states, tooltips, accessible names, and at least 40-pixel touch targets. Text never scales with viewport width and letter spacing remains zero.

## Verification

Verification requires TypeScript and Vite production builds plus browser screenshots at desktop and mobile widths. Screenshots must show the login, empty chat, populated chat, and documents page without clipping, overlap, blank regions, or missing assets. Existing chat, document, evaluation, administration, upload, reference, feedback, and navigation behavior must remain available.
