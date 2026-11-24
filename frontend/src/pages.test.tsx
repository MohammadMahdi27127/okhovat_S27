/** @vitest-environment jsdom */
import React from 'react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { GrowthPage, ProfilePage } from './pages';
import { api, today } from './api';
import { useApp } from './context';

vi.mock('./context', () => ({ useApp: vi.fn() }));
vi.mock('./api', async importOriginal => ({
  ...await importOriginal<typeof import('./api')>(),
  api: vi.fn().mockResolvedValue({}), upload: vi.fn().mockResolvedValue(null),
}));
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', { value: () => ({
    matches: true, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {},
  }) });
  vi.stubGlobal('IntersectionObserver', class {
    observe() {} unobserve() {} disconnect() {}
  });
});
const user = {
  code: 'test-code', name: 'عضو آزمایش در تست', ring: 'حلقه', team: 'آموزش', is_admin: false,
  is_coach: false, is_ring_leader: false, is_workgroup_manager: false, is_concerned_member: false,
};
function context(coach = false, growth: object[] = []) {
  return {
    user: { ...user, is_coach: coach }, attendance: null, loading: false, error: '',
    data: {
      growth, stats: { posts: 2, growth: 4, followers: 7, following: 3 },
      preferences: {}, messages: [], directory: [], archive: [], notifications: [],
      forms: [], answers: [], following: [], ringGrades: {}, groupGrades: {}, landing: [], programPeople: [],
    },
    refresh: vi.fn().mockResolvedValue(undefined), restore: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined), toast: vi.fn(),
  };
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useApp).mockReturnValue(context() as ReturnType<typeof useApp>);
});
afterEach(cleanup);

describe('preserved profile and growth interactions', () => {
  it('renders four profile statistics and an accessible logout icon', () => {
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    for (const label of ['پست', 'دنبال‌کننده', 'دنبال‌شونده', 'گزارش رشد']) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'خروج از حساب' })).toBeInTheDocument();
    expect(screen.getByText('درصد حضور')).toBeInTheDocument();
    expect(screen.getByText('وضعیت من')).toBeInTheDocument();
  });
  it('defaults publication to off and sends false to the API', async () => {
    render(<MemoryRouter><GrowthPage /></MemoryRouter>);
    const checkbox = screen.getByRole('checkbox', { name: /گزارشم در پست‌ها منتشر شود/ });
    expect(checkbox).not.toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'ثبت رشد امروز' }));
    await waitFor(() => expect(api).toHaveBeenCalledWith('growth/', 'PUT', expect.objectContaining({ publish: false })));
  });
  it('preserves explicit publication when editing a report', () => {
    vi.mocked(useApp).mockReturnValue(context(false, [{ userId: user.code, day: today(), sport: 1, reading: 25, publish: true }]) as ReturnType<typeof useApp>);
    render(<MemoryRouter><GrowthPage /></MemoryRouter>);
    expect(screen.getByRole('checkbox', { name: /گزارشم در پست‌ها منتشر شود/ })).toBeChecked();
    expect(screen.getByRole('button', { name: 'به‌روزرسانی گزارش امروز' })).toBeInTheDocument();
  });
  it('shows the two coach grade selectors', () => {
    vi.mocked(useApp).mockReturnValue(context(true) as ReturnType<typeof useApp>);
    render(<MemoryRouter><ProfilePage /></MemoryRouter>);
    expect(screen.getByRole('combobox', { name: 'انتخاب حلقه' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'انتخاب کارگروه' })).toBeInTheDocument();
    expect(screen.queryByText('دنبال‌کننده')).not.toBeInTheDocument();
  });
});
