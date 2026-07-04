import { useEffect, useRef, useState } from 'react';
import { platformSettingsApi } from '../api';

export default function AdminSettingsPage() {
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    platformSettingsApi.getLogo()
      .then(({ data }) => setLogoUrl(data.url))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setMsg({ type: 'err', text: 'Файл слишком большой (макс. 2 МБ)' });
      return;
    }

    setUploading(true);
    setMsg(null);
    try {
      const { data } = await platformSettingsApi.uploadLogo(file);
      setLogoUrl(data.url);
      setMsg({ type: 'ok', text: 'Логотип загружен' });
    } catch (err: any) {
      setMsg({ type: 'err', text: err.response?.data?.detail || 'Ошибка загрузки' });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Удалить логотип?')) return;
    try {
      await platformSettingsApi.deleteLogo();
      setLogoUrl(null);
      setMsg({ type: 'ok', text: 'Логотип удалён' });
    } catch {
      setMsg({ type: 'err', text: 'Ошибка удаления' });
    }
  };

  if (loading) return <div className="text-center py-20 text-surface-300">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Настройки платформы</h1>

      <div className="card max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Логотип</h2>

        {/* Preview */}
        <div className="mb-4 p-4 bg-dark-900 rounded-lg flex items-center justify-center min-h-[80px]">
          {logoUrl ? (
            <img src={logoUrl} alt="Logo" className="max-h-16 object-contain" />
          ) : (
            <span className="text-surface-400 text-sm">Логотип не загружен</span>
          )}
        </div>

        {/* Upload */}
        <div className="flex items-center gap-3 mb-3">
          <label className="btn-primary cursor-pointer inline-block">
            {uploading ? 'Загрузка...' : 'Загрузить логотип'}
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
          {logoUrl && (
            <button onClick={handleDelete} className="text-sm text-red-500 hover:text-red-400 transition-colors">
              Удалить
            </button>
          )}
        </div>

        <p className="text-xs text-surface-400 mb-3">
          PNG, JPG, SVG, WebP или GIF. Максимум 2 МБ. Рекомендуемая высота: 48px.
        </p>

        {msg && (
          <div className={`text-sm p-2 rounded ${msg.type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {msg.text}
          </div>
        )}
      </div>
    </div>
  );
}
