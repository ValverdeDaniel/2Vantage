import { describe, expect, it } from 'vitest';
import { setTotalCap } from './boardConfig';
import { budgetStep, clientBudget, dollars, totalCapOf } from './clientBudget';

const STEPS = [
  { value: null, label: 'Any budget' },
  { value: 5, label: 'Within 5% of current' },
  { value: 10, label: 'Within 10% of current' },
  { value: 15, label: 'Within 15% of current' },
  { value: -5, label: 'At least 5% cheaper' },
  { value: -10, label: 'At least 10% cheaper' },
  { value: -15, label: 'At least 15% cheaper' },
];

describe("the client's budget hints (F139, OQ51)", () => {
  it('reads the stored Goals answers, and nothing when unanswered', () => {
    expect(clientBudget({ budget_target: '62000', acceptable_increase_pct: '8' })).toEqual({ target: 62000, increase: 8 });
    expect(clientBudget({})).toEqual({ target: null, increase: null });
    expect(clientBudget(undefined)).toEqual({ target: null, increase: null });
  });

  it('shows the target as stored, with commas, never rounded', () => {
    expect(dollars(62000)).toBe('$62,000');
    expect(dollars('45000.5')).toBe('$45,000.5');
    expect(dollars(950)).toBe('$950');
  });

  it("applies the most generous budget step inside the client's limit", () => {
    expect(budgetStep(STEPS, 8).value).toBe(5);
    expect(budgetStep(STEPS, 10).value).toBe(10);
    expect(budgetStep(STEPS, 40).value).toBe(15);
    expect(budgetStep(STEPS, 0).value).toBe(-5);
    expect(budgetStep(STEPS, -20)).toBeNull();
    expect(budgetStep(STEPS, null)).toBeNull();
  });

  it("finds this line's monthly total cap, the rule Apply writes", () => {
    const config = setTotalCap({ rules: [] }, 'medical', 62000);
    expect(totalCapOf(config, 'medical')).toBe(62000);
    expect(totalCapOf(config, 'dental')).toBeNull();
  });
});
