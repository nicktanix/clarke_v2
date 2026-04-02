/**
 * Simple TTL cache for CLARKE session context.
 *
 * The before_prompt_build hook fires on every LLM call. We cache the
 * CLARKE context response to avoid hitting the API on every single call.
 * Default TTL is 60 seconds — context refreshes at most once per minute.
 */

export class TTLCache<T> {
  private value: T | null = null;
  private expiresAt: number = 0;

  constructor(private ttlMs: number = 60_000) {}

  get(): T | null {
    if (this.value !== null && Date.now() < this.expiresAt) {
      return this.value;
    }
    return null;
  }

  set(value: T): void {
    this.value = value;
    this.expiresAt = Date.now() + this.ttlMs;
  }

  invalidate(): void {
    this.value = null;
    this.expiresAt = 0;
  }

  /**
   * Get cached value, or fetch and cache a new one.
   */
  async getOrFetch(fetcher: () => Promise<T | null>): Promise<T | null> {
    const cached = this.get();
    if (cached !== null) {
      return cached;
    }

    const fresh = await fetcher();
    if (fresh !== null) {
      this.set(fresh);
    }
    return fresh;
  }
}
