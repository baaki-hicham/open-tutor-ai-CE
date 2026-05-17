<script>
  import { onMount } from "svelte";

  // ─── Niveau de l'étudiant ─────────────────────────────────────────────────
  // Dans ton projet, remplace cette valeur par le vrai niveau
  // récupéré depuis le profil de l'étudiant connecté
  // ex: import { user } from '$lib/stores/user'; $: level = $user.level
  let studentLevel = "débutant"; // "débutant" | "intermédiaire" | "avancé"

  // ─── État ─────────────────────────────────────────────────────────────────
  let status = "loading"; // loading | ready | error
  let exercise = null;
  let errorMessage = "";
  let streamedText = "";

  // ─── Au chargement de la page → générer automatiquement ──────────────────
  onMount(async () => {
    await generateExercise();
  });

  async function generateExercise() {
    status = "loading";
    streamedText = "";
    exercise = null;
    errorMessage = "";

    // Thèmes par niveau — l'IA choisit selon le niveau de l'étudiant
    const themesByLevel = {
      "débutant":      ["affichage", "variables", "opérations mathématiques"],
      "intermédiaire": ["boucles", "conditions", "listes"],
      "avancé":        ["fonctions", "algorithmes", "récursivité"],
    };

    const themes = themesByLevel[studentLevel] || themesByLevel["débutant"];
    const theme  = themes[Math.floor(Math.random() * themes.length)];

    const objectivesByLevel = {
      "débutant":      "créer un programme simple avec des variables et des opérations de base",
      "intermédiaire": "utiliser des boucles et des conditions pour résoudre un problème",
      "avancé":        "implémenter un algorithme complet avec des fonctions",
    };

    try {
      const res = await fetch("/api/blockly/generate/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          theme,
          level: studentLevel,
          objective: objectivesByLevel[studentLevel],
          num_test_cases: studentLevel === "avancé" ? 4 : 3,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erreur serveur");
      }

      // Lire le stream SSE
      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullJson = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));

          if (event.type === "chunk") {
            fullJson += event.content;
            streamedText = fullJson; // afficher la progression
          } else if (event.type === "done") {
            try {
              exercise = JSON.parse(fullJson);
            } catch {
              exercise = null;
            }
            status = "ready";
          } else if (event.type === "error") {
            throw new Error(event.message);
          }
        }
      }

    } catch (e) {
      errorMessage = e.message;
      status = "error";
    }
  }

  // ─── Couleurs par niveau ──────────────────────────────────────────────────
  const levelColors = {
    "débutant":      { bg: "#e8f5e9", text: "#2e7d32", border: "#a5d6a7" },
    "intermédiaire": { bg: "#fff3e0", text: "#e65100", border: "#ffcc80" },
    "avancé":        { bg: "#fce4ec", text: "#880e4f", border: "#f48fb1" },
  };

  // Progression du chargement (nombre de caractères reçus)
  $: progress = Math.min(100, Math.round((streamedText.length / 800) * 100));
</script>

<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

  .page {
    font-family: 'DM Sans', sans-serif;
    background: #f7f5f0;
    color: #1a1a1a;
    padding: 40px;
    max-width: 860px;
    margin: 0 auto;
  }

  /* ── État chargement ── */
  .loading-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 40px;
    gap: 28px;
    text-align: center;
  }

  .ai-orb {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: conic-gradient(#c8f07a, #1a1a1a, #c8f07a);
    animation: spin 2s linear infinite;
    position: relative;
  }
  .ai-orb::after {
    content: "";
    position: absolute;
    inset: 6px;
    background: #f7f5f0;
    border-radius: 50%;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .loading-title {
    font-family: 'DM Serif Display', serif;
    font-size: 26px;
    font-style: italic;
    color: #1a1a1a;
  }
  .loading-sub {
    font-size: 14px;
    color: #888;
    max-width: 320px;
    line-height: 1.6;
  }

  /* Barre de progression */
  .progress-bar-wrap {
    width: 280px;
    height: 4px;
    background: #e0ddd6;
    border-radius: 99px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: #1a1a1a;
    border-radius: 99px;
    transition: width 0.3s ease;
  }

  /* ── Exercice généré ── */
  .exercise-wrap {
    display: flex;
    flex-direction: column;
    gap: 20px;
    animation: fadeUp 0.5s ease;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* Badge niveau + bouton nouveau */
  .top-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .level-badge {
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    border: 1.5px solid;
  }
  .btn-new {
    margin-left: auto;
    padding: 8px 18px;
    background: #1a1a1a;
    color: #c8f07a;
    border: none;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: background 0.15s;
  }
  .btn-new:hover { background: #333; }

  /* Carte principale */
  .card {
    background: #fff;
    border: 1px solid #e8e5de;
    border-radius: 16px;
    overflow: hidden;
  }

  .card-top {
    padding: 28px 32px 24px;
    border-bottom: 1px solid #f0ede6;
  }
  .card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 26px;
    letter-spacing: -0.3px;
    margin-bottom: 10px;
  }
  .card-desc {
    font-size: 15px;
    color: #444;
    line-height: 1.75;
  }

  .card-body {
    padding: 28px 32px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }

  .section-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #aaa;
    margin-bottom: 12px;
  }

  /* Blocs */
  .blocks-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .block-chip {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    background: #f7f5f0;
    border: 1px solid #e8e5de;
    border-radius: 6px;
    padding: 4px 10px;
    color: #555;
  }

  /* Cas de test */
  .tests {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .test-row {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    background: #f7f5f0;
    border-radius: 10px;
    padding: 14px 18px;
  }
  .test-num {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #bbb;
    padding-top: 2px;
    flex-shrink: 0;
  }
  .test-body {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .test-desc { font-size: 13px; color: #666; }
  .test-output {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    background: #1a1a1a;
    color: #c8f07a;
    padding: 4px 10px;
    border-radius: 5px;
    display: inline-block;
  }

  /* Indices */
  .hints {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .hint-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  .hint-dot {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #f0ede6;
    border: 1.5px solid #e0ddd6;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #999;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .hint-text { font-size: 14px; color: #555; line-height: 1.6; }

  /* Erreur */
  .error-wrap {
    background: #fff5f5;
    border: 1px solid #fecaca;
    border-radius: 12px;
    padding: 28px 32px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  .error-title { font-size: 16px; font-weight: 500; color: #991b1b; }
  .error-msg {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    color: #b91c1c;
    line-height: 1.6;
  }
  .btn-retry {
    padding: 10px 20px;
    background: #1a1a1a;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    font-family: 'DM Sans', sans-serif;
  }
  .btn-retry:hover { background: #333; }
</style>

<div class="page">

  <!-- ── Chargement : l'IA génère ────────────────────────────────────────── -->
  {#if status === "loading"}
    <div class="loading-wrapper">
      <div class="ai-orb"></div>
      <div class="loading-title">L'IA prépare ton exercice…</div>
      <div class="loading-sub">
        Adapté à ton niveau <strong>{studentLevel}</strong> —
        ça prend quelques secondes.
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill" style="width: {progress}%"></div>
      </div>
    </div>

  <!-- ── Erreur ───────────────────────────────────────────────────────────── -->
  {:else if status === "error"}
    <div class="error-wrap">
      <div class="error-title">La génération a échoué</div>
      <div class="error-msg">{errorMessage}</div>
      <button class="btn-retry" on:click={generateExercise}>
        ↺ &nbsp;Réessayer
      </button>
    </div>

  <!-- ── Exercice prêt ────────────────────────────────────────────────────── -->
  {:else if status === "ready" && exercise}
    <div class="exercise-wrap">

      <!-- Ligne du haut : niveau + bouton nouvel exercice -->
      <div class="top-row">
        {#if exercise.difficulty}
          <span
            class="level-badge"
            style="
              background: {levelColors[exercise.difficulty]?.bg ?? '#f5f5f5'};
              color: {levelColors[exercise.difficulty]?.text ?? '#333'};
              border-color: {levelColors[exercise.difficulty]?.border ?? '#ddd'};
            "
          >
            {exercise.difficulty}
          </span>
        {/if}
        <button class="btn-new" on:click={generateExercise}>
          ↺ &nbsp;Nouvel exercice
        </button>
      </div>

      <!-- Carte exercice -->
      <div class="card">
        <div class="card-top">
          <div class="card-title">{exercise.title}</div>
          <div class="card-desc">{exercise.description}</div>
        </div>

        <div class="card-body">

          <!-- Blocs autorisés -->
          {#if exercise.allowed_blocks?.length}
            <div>
              <div class="section-label">Blocs disponibles</div>
              <div class="blocks-wrap">
                {#each exercise.allowed_blocks as block}
                  <span class="block-chip">{block}</span>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Cas de test -->
          {#if exercise.test_cases?.length}
            <div>
              <div class="section-label">
                {exercise.test_cases.length} cas de test à réussir
              </div>
              <div class="tests">
                {#each exercise.test_cases as tc, i}
                  <div class="test-row">
                    <span class="test-num">#{i + 1}</span>
                    <div class="test-body">
                      {#if tc.description}
                        <span class="test-desc">{tc.description}</span>
                      {/if}
                      <span class="test-output">{tc.expected_output}</span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Indices -->
          {#if exercise.hints?.length}
            <div>
              <div class="section-label">Indices si tu bloques</div>
              <div class="hints">
                {#each exercise.hints as hint, i}
                  <div class="hint-row">
                    <span class="hint-dot">{i + 1}</span>
                    <span class="hint-text">{hint}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

        </div>
      </div>

    </div>
  {/if}

</div>
