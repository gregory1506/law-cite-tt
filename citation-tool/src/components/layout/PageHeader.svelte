<script>
  let { eyebrow, title, description = "", meta = "", icon = null } = $props();
</script>

<header class="page-heading">
  <div class="page-heading-text">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    {#if description}<p class="description">{description}</p>{/if}
  </div>
  {#if icon || meta}
    <div class="page-heading-aside">
      {#if meta}<p class="meta">{meta}</p>{/if}
      {#if icon}
        <span class="heading-mark" aria-hidden="true">{@render icon()}</span>
      {/if}
    </div>
  {/if}
</header>

<style>
  .page-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-6);
    margin-bottom: var(--space-6);
  }
  .eyebrow {
    margin: 0 0 var(--space-2);
    color: var(--accent);
    font-size: var(--text-xs);
    font-weight: var(--weight-bold);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  h1 {
    margin: 0;
    font-size: var(--text-h1);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
    letter-spacing: -0.01em;
  }
  .description {
    max-width: 650px;
    margin: var(--space-3) 0 0;
    color: var(--muted-strong);
  }
  .page-heading-aside {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex: 0 0 auto;
  }
  .meta {
    margin: 0;
    color: var(--muted);
    font-size: var(--text-sm);
  }
  .heading-mark {
    display: grid;
    width: 50px;
    height: 50px;
    place-items: center;
    border: 1px solid var(--accent-border);
    border-radius: var(--radius);
    background: linear-gradient(145deg, var(--accent-soft), transparent);
    color: var(--accent);
  }
  @media (max-width: 560px) {
    .page-heading {
      align-items: flex-start;
      flex-direction: column;
      gap: var(--space-3);
    }
    .heading-mark { display: none; }
  }
</style>
