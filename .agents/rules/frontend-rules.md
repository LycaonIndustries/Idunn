# Frontend Engineering Rules (React 19 & Tailwind CSS)

## 1. Interaction & DOM Safety
- **Double Submit Protection:** Disable action buttons immediately upon click while an async mutation is pending to prevent duplicate submissions.
- **Zero Console Errors:** Ensure no React runtime warnings, invalid hook usages, or unhandled promise rejections exist.
- **User Feedback:** Provide clear visual feedback (toasts, alert banners, loading skeletons) for both successful actions and errors.

## 2. Accessibility & Affordances
- **Click Affordances:** Interactive elements (buttons, custom links) must display `cursor: pointer` and distinct hover/focus-visible states.
- **Accessible Controls:** Use semantic HTML buttons and anchors rather than non-interactive `<div>` or `<span>` click listeners.

## 3. Styling & Modern React
- **Tailwind Tokens:** Use standard Tailwind utility classes rather than ad-hoc inline styles or arbitrary magic pixel values.
- **React 19 Conventions:** Use idiomatic React 19 hooks and state management; avoid mutating state objects directly.
- **Link Integrity:** Verify that navigation links resolve to valid application routes.
