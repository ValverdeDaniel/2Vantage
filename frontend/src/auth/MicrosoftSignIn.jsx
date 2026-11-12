/**
 * "Sign in with Microsoft" (plan.md §8.2, §11.4; slice 47): a plain form, so the browser itself goes to the firm's
 * Microsoft 365 sign-in and comes back signed in, landing on `next`. Shown only when the server says Microsoft 365
 * sign-in is set up (GET auth/options/). Inside `.page-container > .card > form` the old full-width button rule applies.
 */
export default function MicrosoftSignIn({ start, next }) {
  return (
    <form method="get" action={start}>
      <input type="hidden" name="next" value={next} />
      <button type="submit" className="btn btn-primary">
        Sign in with Microsoft
      </button>
    </form>
  );
}
