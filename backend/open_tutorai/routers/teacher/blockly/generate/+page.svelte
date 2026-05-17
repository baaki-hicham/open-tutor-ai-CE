<script>
  // ─── État du formulaire ───────────────────────────────────────────────────
  let theme = "";
  let level = "débutant";
  let objective = "";
  let courseId = "";
  let numTestCases = 3;
  let allowedBlocksHint = "";

  // ─── État de la génération ────────────────────────────────────────────────
  let status = "idle"; // idle | generating | done | error
  let streamedJson = "";       // JSON brut qui arrive token par token
  let parsedExercise = null;   // objet parsé une fois le streaming terminé
  let assignmentId = null;     // ID retourné par le serveur après sauvegarde
  let errorMessage = "";

  // ─── État publication ─────────────────────────────────────────────────────
  let publishStatus = "idle";  // idle | loading | done | error

  // ─── Lancer la génération en streaming ───────────────────────────────────
  async function generate() {
    if (!theme.trim() || !objective.trim()) return;

    status = "generating";
    streamedJson = "";
    parsedExercise = null;
    assignmentId = null;
    errorMessage = "";

    const body = {
      theme: theme.trim(),
      level,
      objective: objective.trim(),
      num_test_cases: numTestCases,
      course_id: courseId.trim() || null,
      allowed_blocks_hint: allowedBlocksHint.trim()
        ? allowedBlocksHint.split(",").map((b) => b.trim()).filter(Boolean)
        : null,
    };

    try {
      const res = await fetch("/api/blockly/generate/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erreur serveur");
      }

      // Lire le stream SSE ligne par ligne
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // garder la ligne incomplète pour le prochain chunk

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));

          if (event.type === "chunk") {
            streamedJson += event.content;
          } else if (event.type === "done") {
            assignmentId = event.assignment_id;
            // Parser le JSON accumulé
            try {
              parsedExercise = JSON.parse(streamedJson);
            } catch {
              parsedExercise = null;
            }
            status = "done";
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

  // ─── Publier l'exercice ───────────────────────────────────────────────────
  async function publish() {
    if (!assignmentId) return;
    publishStatus = "loading";

    try {
      const res = await fetch(`/api/blockly/assignment/${assignmentId}/publish`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Erreur lors de la publication");
      publishStatus = "done";
    } catch (e) {
      publishStatus = "error";
    }
  }

  // ─── Regénérer ────────────────────────────────────────────────────────────
  function regenerate() {
    status = "idle";
    streamedJson = "";
    parsedExercise = null;
    publishStatus = "idle";
  }

  // ─── Helpers d'affichage ──────────────────────────────────────────────────
  const levelColors = {
    débutant:       { bg: "#e8f5e9", text: "#2e7d32", border: "#a5d6a7" },
    intermédiaire:  { bg: "#fff3e0", text: "#e65100", border: "#ffcc80" },
    avancé:         { bg: "#fce4ec", text: "#880e4f", border: "#f48fb1" },
  };

  $: levelStyle = levelColors[level] || levelColors["débutant"];

  // Indentation du JSON streamé pour le rendre lisible
  $: formattedJson = (() => {
    try {
      return JSON.stringify(JSON.parse(streamedJson), null, 2);
    } catch {
      return streamedJson;
    }
  })();
</script>

<style>
  /* ── Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

  /* ── Variables ── */
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }

  .page {
    background: #f7f5f0;
    font-family: 'DM Sans', sans-serif;
    color: #1a1a1a;
  }

  /* ── Header ── */
  .header {
    background: #1a1a1a;
    color: #f7f5f0;
    padding: 28px 48px;
    display: flex;
    align-items: baseline;
    gap: 16px;
    border-bottom: 3px solid #c8f07a;
  }
  .header-title {
    font-family: 'DM Serif Display', serif;
    font-size: 28px;
    letter-spacing: -0.5px;
  }
  .header-sub {
    font-size: 13px;
    color: #888;
    font-weight: 300;
  }
  .header-badge {
    margin-left: auto;
    background: #c8f07a;
    color: #1a1a1a;
    font-size: 11px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  /* ── Layout ── */
 .layout {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 0;
  }

  /* ── Panneau gauche : formulaire ── */
 .panel-form {
    background: #fff;
    border-right: 1px solid #e8e5de;
    padding: 40px 36px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }

  .panel-title {
    font-family: 'DM Serif Display', serif;
    font-size: 20px;
    color: #1a1a1a;
    padding-bottom: 16px;
    border-bottom: 1px solid #e8e5de;
  }

  /* ── Champs de formulaire ── */
  .field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .field label {
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #666;
  }
  .field input,
  .field textarea,
  .field select {
    font-family: 'DM Sans', sans-serif;
    font-size: 15px;
    border: 1.5px solid #e0ddd6;
    border-radius: 8px;
    padding: 11px 14px;
    background: #fafaf8;
    color: #1a1a1a;
    transition: border-color 0.15s, background 0.15s;
    outline: none;
    resize: none;
  }
  .field input:focus,
  .field textarea:focus,
  .field select:focus {
    border-color: #1a1a1a;
    background: #fff;
  }
  .field textarea { min-height: 90px; line-height: 1.6; }
  .field .hint {
    font-size: 12px;
    color: #999;
    line-height: 1.5;
  }

  /* ── Sélecteur de niveau ── */
  .level-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .level-btn {
    padding: 10px 6px;
    border: 1.5px solid #e0ddd6;
    border-radius: 8px;
    background: #fafaf8;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: #666;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
  }
  .level-btn:hover { border-color: #999; color: #1a1a1a; }
  .level-btn.active {
    border-width: 2px;
    font-weight: 500;
  }

  /* ── Compteur de cas de test ── */
  .counter-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .counter-btn {
    width: 32px; height: 32px;
    border: 1.5px solid #e0ddd6;
    border-radius: 6px;
    background: #fafaf8;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
    color: #1a1a1a;
  }
  .counter-btn:hover { border-color: #1a1a1a; background: #f0ede6; }
  .counter-val {
    font-family: 'DM Mono', monospace;
    font-size: 20px;
    font-weight: 500;
    min-width: 24px;
    text-align: center;
  }
  .counter-label { font-size: 13px; color: #888; }

  /* ── Bouton générer ── */
 .btn-generate {
    padding: 16px;
    background: #1a1a1a;
    color: #c8f07a;
    border: none;
    border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    letter-spacing: 0.2px;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }
  .btn-generate:hover:not(:disabled) {
    background: #333;
    transform: translateY(-1px);
  }
  .btn-generate:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none;
  }

  /* ── Spinner ── */
  .spinner {
    width: 18px; height: 18px;
    border: 2px solid #c8f07a40;
    border-top-color: #c8f07a;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Panneau droit : résultat ── */
  .panel-result {
    padding: 40px 44px;
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  /* ── État vide ── */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    color: #bbb;
    text-align: center;
  }
  .empty-icon {
    font-size: 56px;
    opacity: 0.4;
  }
  .empty-state h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    font-style: italic;
    color: #ccc;
    font-weight: 400;
  }
  .empty-state p {
    font-size: 14px;
    color: #bbb;
    max-width: 300px;
    line-height: 1.6;
  }

  /* ── Bloc JSON en cours de streaming ── */
  .stream-block {
    background: #1a1a1a;
    border-radius: 12px;
    overflow: hidden;
  }
  .stream-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px;
    border-bottom: 1px solid #2a2a2a;
    font-size: 12px;
    color: #666;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .dot-red    { background: #ff5f57; }
  .dot-yellow { background: #febc2e; }
  .dot-green  { background: #28c840; }
  .stream-body {
    padding: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    line-height: 1.8;
    color: #c8f07a;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 420px;
    overflow-y: auto;
  }
  .cursor {
    display: inline-block;
    width: 2px; height: 14px;
    background: #c8f07a;
    margin-left: 2px;
    vertical-align: middle;
    animation: blink 1s step-end infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }

  /* ── Carte exercice (résultat final) ── */
  .exercise-card {
    background: #fff;
    border: 1px solid #e8e5de;
    border-radius: 14px;
    overflow: hidden;
    animation: fadeUp 0.4s ease;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .card-header {
    padding: 24px 28px 20px;
    border-bottom: 1px solid #f0ede6;
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }
  .card-header-text { flex: 1; }
  .card-title {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    letter-spacing: -0.3px;
    margin-bottom: 6px;
  }
  .card-description {
    font-size: 14px;
    color: #555;
    line-height: 1.7;
  }
  .level-pill {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
    border: 1.5px solid;
    flex-shrink: 0;
  }

  .card-body { padding: 24px 28px; display: flex; flex-direction: column; gap: 24px; }

  /* ── Section générique ── */
  .section-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #999;
    margin-bottom: 10px;
  }

  /* ── Blocs autorisés ── */
  .blocks-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .block-tag {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    background: #f7f5f0;
    border: 1px solid #e8e5de;
    border-radius: 6px;
    padding: 4px 10px;
    color: #444;
  }

  /* ── Cas de test ── */
  .test-cases { display: flex; flex-direction: column; gap: 8px; }
  .test-case {
    background: #f7f5f0;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }
  .tc-index {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #bbb;
    margin-top: 1px;
    flex-shrink: 0;
  }
  .tc-body { flex: 1; display: flex; flex-direction: column; gap: 4px; }
  .tc-desc { font-size: 13px; color: #555; }
  .tc-output {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: #1a1a1a;
    background: #eceae3;
    padding: 3px 8px;
    border-radius: 4px;
    display: inline-block;
  }

  /* ── Indices ── */
  .hints { display: flex; flex-direction: column; gap: 6px; }
  .hint-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 14px;
    color: #555;
    line-height: 1.5;
  }
  .hint-num {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    background: #1a1a1a;
    color: #c8f07a;
    width: 20px; height: 20px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  /* ── Actions ── */
  .actions {
    display: flex;
    gap: 10px;
    padding-top: 4px;
  }
  .btn {
    padding: 12px 20px;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    border: none;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .btn-primary {
    background: #1a1a1a;
    color: #c8f07a;
    flex: 1;
  }
  .btn-primary:hover:not(:disabled) { background: #333; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-secondary {
    background: #f0ede6;
    color: #555;
  }
  .btn-secondary:hover { background: #e8e5de; color: #1a1a1a; }

  /* ── Succès publication ── */
  .publish-success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: fadeUp 0.3s ease;
  }
  .publish-success-icon { font-size: 22px; }
  .publish-success-text { font-size: 14px; color: #166534; line-height: 1.5; }
  .publish-success-text strong { font-weight: 500; display: block; }

  /* ── Erreur ── */
  .error-box {
    background: #fff5f5;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .error-title { font-size: 15px; font-weight: 500; color: #991b1b; }
  .error-msg { font-size: 13px; color: #b91c1c; line-height: 1.6; font-family: 'DM Mono', monospace; }
  .btn-retry {
    align-self: flex-start;
    padding: 8px 16px;
    background: #1a1a1a;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
  }
</style>

<div class="page">

  <!-- Header -->
  <header class="header">
    <h1 class="header-title">Générateur d'exercices</h1>
    <span class="header-sub">Blockly × IA</span>
    <span class="header-badge">Espace enseignant</span>
  </header>

  <div class="layout">

    <!-- ── Panneau gauche : formulaire ───────────────────────────────────── -->
    <aside class="panel-form">
      <h2 class="panel-title">Configurer l'exercice</h2>

      <!-- Thème -->
      <div class="field">
        <label for="theme">Thème</label>
        <input
          id="theme"
          type="text"
          placeholder="ex : boucles, conditions, listes…"
          bind:value={theme}
          disabled={status === "generating"}
        />
      </div>

      <!-- Niveau -->
      <div class="field">
        <label>Niveau</label>
        <div class="level-grid">
          {#each ["débutant", "intermédiaire", "avancé"] as l}
            <button
              class="level-btn"
              class:active={level === l}
              style={level === l
                ? `background:${levelColors[l].bg}; color:${levelColors[l].text}; border-color:${levelColors[l].border};`
                : ""}
              on:click={() => (level = l)}
              disabled={status === "generating"}
            >
              {l}
            </button>
          {/each}
        </div>
      </div>

      <!-- Objectif -->
      <div class="field">
        <label for="objective">Objectif pédagogique</label>
        <textarea
          id="objective"
          placeholder="ex : afficher les nombres de 1 à N avec une boucle for"
          bind:value={objective}
          disabled={status === "generating"}
        ></textarea>
        <span class="hint">
          Plus l'objectif est précis, meilleur sera l'exercice généré.
        </span>
      </div>

      <!-- Nombre de cas de test -->
      <div class="field">
        <label>Cas de test</label>
        <div class="counter-row">
          <button
            class="counter-btn"
            on:click={() => (numTestCases = Math.max(1, numTestCases - 1))}
            disabled={status === "generating"}
          >−</button>
          <span class="counter-val">{numTestCases}</span>
          <button
            class="counter-btn"
            on:click={() => (numTestCases = Math.min(10, numTestCases + 1))}
            disabled={status === "generating"}
          >+</button>
          <span class="counter-label">cas à générer</span>
        </div>
      </div>

      <!-- ID du cours (optionnel) -->
      <div class="field">
        <label for="courseId">ID du cours <span style="font-weight:300;text-transform:none">(optionnel)</span></label>
        <input
          id="courseId"
          type="text"
          placeholder="ex : cours-python-L1"
          bind:value={courseId}
          disabled={status === "generating"}
        />
      </div>

      <!-- Blocs suggérés (optionnel) -->
      <div class="field">
        <label for="blocks">Blocs suggérés <span style="font-weight:300;text-transform:none">(optionnel)</span></label>
        <input
          id="blocks"
          type="text"
          placeholder="controls_repeat_ext, math_number…"
          bind:value={allowedBlocksHint}
          disabled={status === "generating"}
        />
        <span class="hint">Séparés par des virgules. Laisse vide pour laisser l'IA choisir.</span>
      </div>

      <!-- Bouton -->
      <button
        class="btn-generate"
        on:click={generate}
        disabled={status === "generating" || !theme.trim() || !objective.trim()}
      >
        {#if status === "generating"}
          <span class="spinner"></span>
          Génération en cours…
        {:else}
          ✦ &nbsp;Générer l'exercice
        {/if}
      </button>
    </aside>

    <!-- ── Panneau droit : résultat ──────────────────────────────────────── -->
    <main class="panel-result">

      <!-- État vide -->
      {#if status === "idle"}
        <div class="empty-state">
          <div class="empty-icon">◈</div>
          <h2>En attente de génération</h2>
          <p>
            Remplis le formulaire à gauche et clique sur
            <em>Générer l'exercice</em> — l'IA construira
            un exercice Blockly complet en quelques secondes.
          </p>
        </div>

      <!-- Streaming en cours -->
      {:else if status === "generating"}
        <div class="stream-block">
          <div class="stream-header">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
            <span style="margin-left:8px">L'IA génère l'exercice…</span>
          </div>
          <div class="stream-body">
            {formattedJson || "…"}<span class="cursor"></span>
          </div>
        </div>

      <!-- Erreur -->
      {:else if status === "error"}
        <div class="error-box">
          <div class="error-title">La génération a échoué</div>
          <div class="error-msg">{errorMessage}</div>
          <button class="btn-retry" on:click={() => (status = "idle")}>
            Réessayer
          </button>
        </div>

      <!-- Résultat final -->
      {:else if status === "done"}

        <!-- Succès publication -->
        {#if publishStatus === "done"}
          <div class="publish-success">
            <span class="publish-success-icon">✓</span>
            <div class="publish-success-text">
              <strong>Exercice publié</strong>
              Les étudiants peuvent maintenant y accéder.
            </div>
          </div>
        {/if}

        <!-- Carte exercice -->
        {#if parsedExercise}
          <div class="exercise-card">
            <div class="card-header">
              <div class="card-header-text">
                <div class="card-title">{parsedExercise.title}</div>
                <div class="card-description">{parsedExercise.description}</div>
              </div>
              {#if parsedExercise.difficulty}
                <span
                  class="level-pill"
                  style="background:{levelColors[parsedExercise.difficulty]?.bg ?? '#f5f5f5'};
                         color:{levelColors[parsedExercise.difficulty]?.text ?? '#333'};
                         border-color:{levelColors[parsedExercise.difficulty]?.border ?? '#ddd'};"
                >
                  {parsedExercise.difficulty}
                </span>
              {/if}
            </div>

            <div class="card-body">

              <!-- Blocs autorisés -->
              {#if parsedExercise.allowed_blocks?.length}
                <div>
                  <div class="section-label">Blocs autorisés</div>
                  <div class="blocks-grid">
                    {#each parsedExercise.allowed_blocks as block}
                      <span class="block-tag">{block}</span>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Cas de test -->
              {#if parsedExercise.test_cases?.length}
                <div>
                  <div class="section-label">
                    {parsedExercise.test_cases.length} cas de test
                  </div>
                  <div class="test-cases">
                    {#each parsedExercise.test_cases as tc, i}
                      <div class="test-case">
                        <span class="tc-index">#{i + 1}</span>
                        <div class="tc-body">
                          {#if tc.description}
                            <span class="tc-desc">{tc.description}</span>
                          {/if}
                          <span class="tc-output">{tc.expected_output}</span>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Indices -->
              {#if parsedExercise.hints?.length}
                <div>
                  <div class="section-label">{parsedExercise.hints.length} indices</div>
                  <div class="hints">
                    {#each parsedExercise.hints as hint, i}
                      <div class="hint-row">
                        <span class="hint-num">{i + 1}</span>
                        <span>{hint}</span>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

            </div>
          </div>

          <!-- Actions -->
          <div class="actions">
            <button
              class="btn btn-primary"
              on:click={publish}
              disabled={publishStatus === "loading" || publishStatus === "done"}
            >
              {#if publishStatus === "loading"}
                <span class="spinner" style="border-color:#c8f07a40; border-top-color:#c8f07a;"></span>
                Publication…
              {:else if publishStatus === "done"}
                ✓ &nbsp;Publié
              {:else}
                ↑ &nbsp;Publier pour les étudiants
              {/if}
            </button>
            <button class="btn btn-secondary" on:click={regenerate}>
              ↺ &nbsp;Regénérer
            </button>
          </div>

        {:else}
          <!-- JSON non parseable : affichage brut -->
          <div class="stream-block">
            <div class="stream-header">
              <span class="dot dot-yellow"></span>
              <span style="margin-left:8px">Réponse brute (JSON invalide)</span>
            </div>
            <div class="stream-body">{streamedJson}</div>
          </div>
          <button class="btn btn-secondary" style="align-self:flex-start" on:click={regenerate}>
            ↺ Réessayer
          </button>
        {/if}

      {/if}
    </main>
  </div>
</div>