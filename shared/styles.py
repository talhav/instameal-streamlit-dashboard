import streamlit as st

def inject_styles():
    st.markdown(
        """
        <style>
        /* ── Card shell ── */
        .reco-card {
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 16px;
            overflow: hidden;
            background: linear-gradient(160deg, rgba(22, 30, 44, 0.97), rgba(12, 17, 26, 0.97));
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.30), inset 0 1px 0 rgba(255, 255, 255, 0.05);
            margin-bottom: 18px;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
            position: relative;
            display: flex;
            flex-direction: row;
            align-items: stretch;
        }
        .reco-card:hover {
            border-color: rgba(255, 193, 7, 0.30);
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.08);
            transform: translateY(-4px);
        }

        /* ── Image ── */
        .reco-card-image-wrapper {
            position: relative;
            width: 240px;
            flex-shrink: 0;
            min-height: 180px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.25);
        }
        .reco-card-image-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 0.35s ease;
        }
        .reco-card:hover .reco-card-image-wrapper img { transform: scale(1.07); }
        .reco-card-no-image {
            width: 240px;
            flex-shrink: 0;
            min-height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, rgba(30,40,55,0.8), rgba(15,20,28,0.9));
            color: rgba(255,255,255,0.25);
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.5px;
        }
        .reco-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #ffc107, #ff9800);
            color: #111;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.70rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            z-index: 10;
        }

        /* ── Body ── */
        .reco-card-content {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 0;
        }
        .reco-card-body {
            padding: 14px 16px 6px 16px;
            flex: 1;
        }
        .reco-card-title {
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.35;
            margin: 0 0 6px 0;
            color: #ffffff;
            letter-spacing: -0.3px;
        }
        .reco-card-description {
            font-size: 0.80rem;
            line-height: 1.45;
            color: rgba(255, 255, 255, 0.55);
            margin: 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        /* ── Ranked Reasoning (NEW) ── */
        .reco-rank-reasoning {
            padding: 12px 16px 4px 16px;
            font-size: 0.80rem;
            color: #d1d5db;
            line-height: 1.4;
            background: rgba(0, 0, 0, 0.15);
            border-left: 2px solid #3b82f6;
            margin-top: 10px;
            font-style: italic;
        }

        /* ── Nutrition strip ── */
        .reco-nut-section {
            padding: 10px 16px 14px 16px;
            border-top: 1px solid rgba(255, 193, 7, 0.12);
            margin-top: auto;
        }
        .reco-nut-heading {
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: rgba(255, 193, 7, 0.60);
            margin-bottom: 9px;
        }
        .reco-nut-row {
            display: flex;
            gap: 6px;
        }
        .reco-nut-pill {
            flex: 1;
            min-width: 0;
            background: rgba(255, 193, 7, 0.07);
            border-left: 2px solid rgba(255, 193, 7, 0.55);
            border-radius: 0 7px 7px 0;
            padding: 6px 8px 6px 9px;
            display: flex;
            flex-direction: column;
            gap: 2px;
            transition: background 0.2s ease, border-color 0.2s ease;
        }
        .reco-nut-pill:hover {
            background: rgba(255, 193, 7, 0.13);
            border-color: #ffc107;
        }
        .reco-nut-val {
            font-size: 0.88rem;
            font-weight: 800;
            color: #ffc107;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.1;
        }
        .reco-nut-lbl {
            font-size: 0.60rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.40);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .reco-nut-empty {
            padding: 8px 16px 12px 16px;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.25);
            font-style: italic;
        }

        /* ── Dynamic form entry cards (Nth Rec page) ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid rgba(255, 193, 7, 0.18) !important;
            border-radius: 14px !important;
            background: linear-gradient(160deg, rgba(22, 30, 44, 0.80), rgba(12, 17, 26, 0.80)) !important;
            margin-bottom: 10px !important;
            transition: border-color 0.25s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(255, 193, 7, 0.38) !important;
        }
        .entry-card-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: rgba(255, 193, 7, 0.75);
            margin-bottom: 4px;
        }
        .section-header-strip {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }

        /* ── Meal section header ── */
        .meal-section {
            margin-top: 24px;
            margin-bottom: 12px;
            padding-top: 12px;
            border-top: 2px solid rgba(255, 193, 7, 0.2);
        }
        .meal-section h3 {
            margin-bottom: 2px;
            color: #ffc107;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.95rem;
            font-weight: 700;
        }

        /* ── Feedback Rating Buttons ── */
        .feedback-rating-container {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            align-items: center;
        }
        .feedback-rating-button {
            flex: 1;
            padding: 12px 20px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            color: rgba(255, 255, 255, 0.8);
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .feedback-rating-button:hover {
            border-color: rgba(255, 255, 255, 0.4);
            background: rgba(255, 255, 255, 0.08);
        }
        .feedback-rating-selected-like {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.25), rgba(22, 163, 74, 0.15));
            border-color: #22c55e;
            color: #86efac;
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.2), inset 0 0 10px rgba(34, 197, 94, 0.1);
        }
        .feedback-rating-selected-dislike {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(220, 38, 38, 0.15));
            border-color: #ef4444;
            color: #fca5a5;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.2), inset 0 0 10px rgba(239, 68, 68, 0.1);
        }
        .feedback-rating-indicator {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.90rem;
            font-weight: 600;
            text-align: center;
            min-width: 120px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        .feedback-rating-indicator-like {
            background: rgba(34, 197, 94, 0.15);
            border-color: #22c55e;
            color: #86efac;
        }
        .feedback-rating-indicator-dislike {
            background: rgba(239, 68, 68, 0.15);
            border-color: #ef4444;
            color: #fca5a5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
