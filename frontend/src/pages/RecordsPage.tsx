import { useParams } from 'react-router-dom';
import type { DataType } from '../types';

const DATA_TYPE_LABELS: Record<string, string> = {
  part: 'Parts',
  document: 'Documents',
  conversion: 'Conversion',
};

interface RecordsPageProps {
  forcedDataType?: DataType;
}

export default function RecordsPage({ forcedDataType }: RecordsPageProps = {}) {
  const { dataType } = useParams<{ dataType: string }>();
  const dt = forcedDataType ?? ((dataType as DataType) || 'part');

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">{DATA_TYPE_LABELS[dt] || dt} - Data Analysis</h2>
        </div>
      </div>
    </div>
  );
}
