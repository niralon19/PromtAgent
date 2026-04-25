import { ConfidenceBar } from '@/components/common/ConfidenceBar';
import type { InvestigationResult } from '@/lib/types';

interface Props {
  investigation: InvestigationResult;
}

const STRENGTH_COLOR: Record<string, string> = {
  strong: 'text-resolved',
  moderate: 'text-warning',
  weak: 'text-muted-foreground',
};

export function AnalysisPanel({ investigation }: Props) {
  const { hypothesis, confidence, confidence_rationale, evidence_chain, alternatives_considered, suggested_action } =
    investigation;

  return (
    <div className="space-y-6">
      {/* Hypothesis */}
      <section>
        <h3 className="mb-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Root Cause Hypothesis
        </h3>
        <p className="text-sm">{hypothesis}</p>
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
            <span>Confidence</span>
            <span>{confidence}%</span>
          </div>
          <ConfidenceBar value={confidence} showLabel={false} />
          {confidence_rationale && (
            <p className="mt-1 text-xs text-muted-foreground">{confidence_rationale}</p>
          )}
        </div>
      </section>

      {/* Suggested Action */}
      <section>
        <h3 className="mb-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Suggested Action
        </h3>
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm">{suggested_action.action_key}</span>
            <span
              className={
                suggested_action.estimated_risk === 'high'
                  ? 'text-xs text-red-500'
                  : suggested_action.estimated_risk === 'medium'
                  ? 'text-xs text-warning'
                  : 'text-xs text-muted-foreground'
              }
            >
              {suggested_action.estimated_risk} risk · Tier {suggested_action.tier}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{suggested_action.rationale}</p>
          {suggested_action.requires_approval && (
            <p className="mt-1 text-xs text-warning">⚠ Requires approval before execution</p>
          )}
        </div>
      </section>

      {/* Evidence Chain */}
      {evidence_chain.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
            Evidence Chain
          </h3>
          <ul className="space-y-2">
            {evidence_chain.map((e, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <span className={`mt-0.5 text-xs ${STRENGTH_COLOR[e.strength] ?? ''}`}>●</span>
                <div>
                  <span>{e.claim}</span>
                  <span className="ml-2 text-xs text-muted-foreground">via {e.source_tool}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Alternatives */}
      {alternatives_considered.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground uppercase tracking-wider">
            Alternatives Considered
          </h3>
          <ul className="space-y-2">
            {alternatives_considered.map((a, i) => (
              <li key={i} className="text-sm">
                <span className="line-through text-muted-foreground">{a.hypothesis}</span>
                <span className="ml-2 text-xs text-muted-foreground">— {a.why_rejected}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
