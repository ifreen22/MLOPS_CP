import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test } from 'vitest';
import { ThemeProvider } from './ThemeProvider';
import { ThemeToggle } from './ThemeToggle';

const storageKey = 'theme-toggle-test';

beforeEach(() => {
  document.documentElement.className = '';
  localStorage.clear();
});

afterEach(() => {
  document.documentElement.className = '';
  localStorage.clear();
});

test('toggles the document theme and persists the selected preference', async () => {
  const user = userEvent.setup();

  render(
    <ThemeProvider defaultTheme="light" storageKey={storageKey}>
      <ThemeToggle />
    </ThemeProvider>,
  );

  expect(document.documentElement).toHaveClass('light');
  await user.click(screen.getByRole('button', { name: 'Toggle theme' }));

  expect(document.documentElement).toHaveClass('dark');
  expect(localStorage.getItem(storageKey)).toBe('dark');
});
