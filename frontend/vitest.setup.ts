import "@testing-library/jest-dom/vitest";

// jsdom has no layout engine, so it doesn't implement scrollIntoView.
Element.prototype.scrollIntoView ??= () => {};
