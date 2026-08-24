import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, BrainCircuit, ShieldAlert, FileMinus } from 'lucide-react';

export default function FailureBadge({ failureType, success }) {
  if (success || failureType === 'No Failure') {
    return (
      <span className="badge badge-success">
        <CheckCircle2 size={13} />
        Success (No Failure)
      </span>
    );
  }

  const ft = failureType || 'Wrong Final Answer';

  if (ft === 'Premature Agreement') {
    return (
      <span className="badge badge-warning">
        <AlertTriangle size={13} />
        Premature Agreement
      </span>
    );
  }

  if (ft === 'Information Loss') {
    return (
      <span className="badge badge-warning">
        <FileMinus size={13} />
        Information Loss
      </span>
    );
  }

  if (ft === 'Hallucination / Unsupported Claim') {
    return (
      <span className="badge badge-danger">
        <BrainCircuit size={13} />
        Hallucination / Unsupported Claim
      </span>
    );
  }

  if (ft === 'Contradiction') {
    return (
      <span className="badge badge-danger">
        <ShieldAlert size={13} />
        Contradiction
      </span>
    );
  }

  return (
    <span className="badge badge-danger">
      <XCircle size={13} />
      {ft}
    </span>
  );
}
