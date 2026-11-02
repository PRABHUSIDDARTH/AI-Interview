import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api, { extractResumeSkills } from '../services/api';
import GlassCard from '../components/GlassCard';
import Button from '../components/Button';
import {
  IconArrowLeft,
  IconArrowRight,
  IconUpload,
  IconFilePdf,
  IconCheck,
  IconSparkles,
} from '../components/Icons';

const INTERVIEW_TYPES = ['Technical', 'HR', 'Mixed', 'Behavioral'];
const EXPERIENCE_LEVELS = ['Beginner', 'Intermediate', 'Advanced'];
const DIFFICULTIES = ['Easy', 'Medium', 'Hard'];
const QUESTION_COUNTS = [3, 5, 10];
const LANGUAGES = ['English', 'Tamil', 'Hindi', 'Telugu', 'Kannada', 'Malayalam', 'Other'];

function OptionGroup({ label, options, value, onChange, fieldName, error, description }) {
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
          {label}
        </label>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
      <div className="flex flex-wrap gap-2.5">
        {options.map((opt) => {
          const strOpt = String(opt);
          const isSelected = String(value) === strOpt;
          return (
            <button
              key={strOpt}
              type="button"
              onClick={() => onChange(fieldName, opt)}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500/50 flex items-center gap-2 ${
                isSelected
                  ? 'bg-primary-600/20 border-primary-500 text-white shadow-glow-primary'
                  : 'glass-panel text-slate-300 hover:text-white hover:border-white/20'
              }`}
            >
              {isSelected && <IconCheck className="w-3.5 h-3.5 text-accent-cyan" />}
              <span>{strOpt}</span>
            </button>
          );
        })}
      </div>
      {error && <p className="text-rose-400 text-xs font-medium mt-1">{error}</p>}
    </div>
  );
}

// Skill selection chip — glowing when selected
function SkillChip({ skill, selected, onToggle }) {
  return (
    <button
      type="button"
      onClick={() => onToggle(skill)}
      className={`relative px-4 py-2.5 rounded-xl text-xs font-bold border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-accent-cyan/50 flex items-center gap-2 select-none ${
        selected
          ? 'bg-accent-cyan/15 border-accent-cyan text-white shadow-[0_0_12px_rgba(34,211,238,0.35)]'
          : 'glass-panel text-slate-300 border-white/10 hover:border-accent-cyan/40 hover:text-white hover:bg-white/[0.06]'
      }`}
      aria-pressed={selected}
      aria-label={`${selected ? 'Deselect' : 'Select'} ${skill}`}
    >
      <span
        className={`w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
          selected
            ? 'bg-accent-cyan border-accent-cyan'
            : 'border-white/25 bg-transparent'
        }`}
      >
        {selected && (
          <svg className="w-2.5 h-2.5 text-slate-900" fill="none" viewBox="0 0 10 10">
            <path d="M2 5l2.5 2.5L8 2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </span>
      <span>{skill}</span>
    </button>
  );
}

export default function InterviewSetupPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const recState = location.state || {};
  const initialType = recState.interview_type || 'Technical';
  const initialRole = recState.job_role || 'Software Developer';
  const initialDifficulty = recState.difficulty || 'Medium';
  const initialLevel = recState.experience_level || 'Intermediate';
  const initialSelected = recState.selected_skills || [];

  // Wizard Step: 1=Resume, 2=Skill Selection, 3=Language & Role, 4=Options, 5=Review & Start
  const STORAGE_KEY = 'ai_interview_setup_draft';

  const loadSavedState = () => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.warn('Failed to parse saved setup state', e);
    }
    return null;
  };

  const savedState = loadSavedState() || {};

  // Wizard Step: 1=Resume, 2=Skill Selection, 3=Language & Role, 4=Options, 5=Review & Start
  const [currentStep, setCurrentStep] = useState(
    savedState.currentStep || (recState.is_recommended ? (initialSelected.length > 0 ? 3 : 2) : 1)
  );

  const [form, setForm] = useState({
    interview_type: savedState.interview_type || initialType,
    job_role: savedState.job_role || initialRole,
    experience_level: savedState.experience_level || initialLevel,
    job_description: savedState.job_description || (recState.focus_topic ? `Coach Recommended Practice: ${recState.focus_topic}` : ''),
    difficulty: savedState.difficulty || initialDifficulty,
    question_count: savedState.question_count || 5,
    interview_language: savedState.interview_language || 'English',
    custom_language: savedState.custom_language || '',
  });

  const [resumeFile, setResumeFile] = useState(null);
  const [resumeFileName, setResumeFileName] = useState(savedState.resumeFileName || '');
  const [extracting, setExtracting] = useState(false);
  const [detectedSkills, setDetectedSkills] = useState(savedState.detectedSkills || initialSelected);
  const [selectedSkills, setSelectedSkills] = useState(savedState.selectedSkills || initialSelected);
  const [isEditingRole, setIsEditingRole] = useState(false);

  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);

  // Sync state to sessionStorage whenever key setup values change
  React.useEffect(() => {
    try {
      const stateToSave = {
        currentStep,
        interview_type: form.interview_type,
        job_role: form.job_role,
        experience_level: form.experience_level,
        job_description: form.job_description,
        difficulty: form.difficulty,
        question_count: form.question_count,
        interview_language: form.interview_language,
        custom_language: form.custom_language,
        resumeFileName,
        detectedSkills,
        selectedSkills,
      };
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
    } catch (e) {
      console.warn('Failed to persist setup draft to sessionStorage', e);
    }
  }, [currentStep, form, resumeFileName, detectedSkills, selectedSkills]);

  const handleSelect = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const handleResumeFileSelect = async (file) => {
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setErrors((prev) => ({ ...prev, resume: 'Resume must be a valid PDF file.' }));
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setErrors((prev) => ({ ...prev, resume: 'Resume exceeds 2 MiB size limit.' }));
      return;
    }
    setResumeFile(file);
    setResumeFileName(file.name);
    setErrors((prev) => ({ ...prev, resume: '' }));

    // Extract skills automatically
    setExtracting(true);
    try {
      const formData = new FormData();
      formData.append('resume', file);
      const { data } = await extractResumeSkills(formData);
      const profile = data?.profile || {};
      const skills = profile.skills || profile.extracted_skills || (profile.profile && profile.profile.skills) || [];
      const role = profile.inferred_role || (profile.profile && profile.profile.inferred_role) || '';

      if (skills && skills.length > 0) {
        setDetectedSkills(skills);
        setSelectedSkills(skills);
      }
      if (role) {
        setForm((prev) => ({ ...prev, job_role: role }));
      }
    } catch (err) {
      console.warn('Skill extraction failed:', err);
    } finally {
      setExtracting(false);
    }
  };

  const toggleSkill = (skill) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  };

  const selectAllSkills = () => setSelectedSkills([...detectedSkills]);
  const clearAllSkills = () => setSelectedSkills([]);

  const handleNextStep = () => {
    if (currentStep === 1) {
      setCurrentStep(2);
    } else if (currentStep === 2) {
      // If skills detected, require at least one selected
      if (detectedSkills.length > 0 && selectedSkills.length === 0) {
        setErrors((prev) => ({ ...prev, skills: 'Please select at least one skill to focus on.' }));
        return;
      }
      setErrors((prev) => ({ ...prev, skills: '' }));
      setCurrentStep(3);
    } else if (currentStep === 3) {
      if (!form.job_role.trim()) {
        setErrors({ job_role: 'Please enter a target job role.' });
        return;
      }
      setCurrentStep(4);
    } else if (currentStep === 4) {
      setCurrentStep(5);
    }
  };

  const handlePrevStep = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setApiError('');
    setLoading(true);

    const activeLanguage =
      form.interview_language === 'Other' && form.custom_language.trim()
        ? form.custom_language.trim()
        : form.interview_language;

    try {
      const formData = new FormData();
      formData.append('interview_type', form.interview_type || 'Technical');
      formData.append('job_role', form.job_role.trim() || 'Software Developer');
      formData.append('experience_level', form.experience_level || 'Intermediate');
      formData.append('difficulty', form.difficulty || 'Medium');
      formData.append('question_count', String(form.question_count || 5));
      formData.append('interview_language', activeLanguage);
      formData.append('resume_skills', JSON.stringify(detectedSkills));
      // Pass the user's skill focus selection
      formData.append('selected_skills', JSON.stringify(selectedSkills));

      if (form.job_description.trim()) {
        formData.append('job_description', form.job_description.trim());
      }
      if (resumeFile) {
        formData.append('resume', resumeFile);
      }

      const response = await api.post('/interviews/start', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = response.data;
      sessionStorage.removeItem(STORAGE_KEY);
      navigate(`/interview/${data.session_id}`);
    } catch (err) {
      const raw = err?.response?.data?.detail;
      let detail;
      if (Array.isArray(raw)) {
        detail = raw.map((d) => d.msg || JSON.stringify(d)).join(', ');
      } else if (typeof raw === 'string') {
        detail = raw;
      } else {
        detail = 'Failed to create interview session. Please try again.';
      }
      setApiError(detail);
    } finally {
      setLoading(false);
    }
  };

  const STEPS = [
    { num: 1, label: 'Upload Resume' },
    { num: 2, label: 'Focus Skills' },
    { num: 3, label: 'Language & Role' },
    { num: 4, label: 'Setup Options' },
    { num: 5, label: 'Start Interview' },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-12">
      {/* Top Breadcrumb & Header */}
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors group"
        >
          <IconArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span>Back to Dashboard</span>
        </button>

        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <span>AI Interview Setup</span>
            <span className="p-1.5 rounded-xl bg-primary-600/20 text-primary-400 border border-primary-500/30">
              <IconSparkles className="w-5 h-5" />
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Resume-driven, skill-focused question personalisation in 5 simple steps.
          </p>
        </div>
      </div>

      {/* Progress Wizard Indicator */}
      <div className="grid grid-cols-5 gap-1.5 glass-panel p-2 rounded-2xl border-white/10">
        {STEPS.map((step) => {
          const isActive = currentStep === step.num;
          const isDone = currentStep > step.num;
          return (
            <button
              key={step.num}
              type="button"
              onClick={() => setCurrentStep(step.num)}
              className={`p-2.5 rounded-xl text-left transition-all ${
                isActive
                  ? 'bg-primary-600/25 border border-primary-500/50 shadow-glow-primary/20'
                  : isDone
                  ? 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]'
                  : 'text-slate-500 hover:text-slate-400'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                    isActive
                      ? 'bg-primary-500 text-white'
                      : isDone
                      ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/40'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {isDone ? '✓' : step.num}
                </span>
                <span className={`text-[10px] font-semibold truncate ${isActive ? 'text-white' : 'text-slate-400'}`}>
                  {step.label}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Step Contents */}
      <form onSubmit={handleSubmit} className="space-y-6">

        {/* ─── STEP 1: RESUME UPLOAD ─── */}
        {currentStep === 1 && (
          <GlassCard className="space-y-6">
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Step 1: Upload Your Resume</span>
                <span className="text-xs text-accent-cyan font-normal lowercase">(Recommended)</span>
              </h2>
              <p className="text-xs text-slate-400">
                Upload your resume PDF to automatically extract candidate skills, frameworks, and job role.
              </p>
            </div>

            {/* PDF File Upload Box */}
            <div className="relative">
              <label
                htmlFor="input-resume-wizard"
                className={`flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed cursor-pointer transition-all ${
                  resumeFile || resumeFileName
                    ? 'bg-primary-600/10 border-primary-500/50 text-white'
                    : 'glass-panel hover:bg-white/[0.05] border-white/15 text-slate-400'
                }`}
              >
                <div className="p-3 rounded-2xl bg-white/5 text-primary-400 mb-3">
                  {extracting ? (
                    <div className="w-6 h-6 rounded-full border-2 border-primary-500 border-t-transparent animate-spin" />
                  ) : resumeFile || resumeFileName ? (
                    <IconFilePdf className="w-8 h-8 text-primary-400" />
                  ) : (
                    <IconUpload className="w-8 h-8 text-slate-400" />
                  )}
                </div>
                <p className="text-sm font-bold text-white">
                  {extracting
                    ? 'Extracting Candidate Skills...'
                    : resumeFile
                    ? resumeFile.name
                    : resumeFileName
                    ? resumeFileName
                    : 'Click or Drag & Drop PDF Resume'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {resumeFile
                    ? `✓ ${(resumeFile.size / 1024 / 1024).toFixed(2)} MB attached`
                    : resumeFileName
                    ? `✓ Attached (${resumeFileName})`
                    : 'Supports PDF up to 2 MB'}
                </p>
              </label>
              <input
                id="input-resume-wizard"
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => handleResumeFileSelect(e.target.files[0])}
              />
            </div>

            {/* Detected Skills Preview (non-selectable here, just a preview) */}
            {detectedSkills.length > 0 && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">✓ Detected Skills</span>
                  <span className="text-[10px] text-accent-cyan px-2 py-0.5 rounded-full bg-accent-cyan/10 border border-accent-cyan/30">
                    {detectedSkills.length} Found
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {detectedSkills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary-600/20 text-primary-300 border border-primary-500/30"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-accent-cyan">
                  ✓ You'll choose which skills to focus on in the next step.
                </p>
              </div>
            )}

            {errors.resume && <p className="text-rose-400 text-xs font-medium">{errors.resume}</p>}

            <div className="flex justify-between items-center pt-4 border-t border-white/[0.06]">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="text-xs text-slate-400 hover:text-slate-200 underline"
              >
                Skip resume upload & proceed
              </button>

              <Button
                type="button"
                variant="primary"
                onClick={handleNextStep}
                icon={IconArrowRight}
                iconPosition="right"
                className="px-6 py-2.5 rounded-xl"
              >
                Continue to Skill Selection
              </Button>
            </div>
          </GlassCard>
        )}

        {/* ─── STEP 2: SKILL SELECTION ─── */}
        {currentStep === 2 && (
          <GlassCard className="space-y-6">
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Step 2: Choose Your Interview Focus</span>
                <span className="p-1 rounded-lg bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20">
                  <IconSparkles className="w-3.5 h-3.5" />
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Choose the skills you want the AI interviewer to focus on. All generated questions will primarily target your selected skills.
              </p>
            </div>

            {detectedSkills.length === 0 ? (
              /* No resume uploaded */
              <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.03] text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center mx-auto">
                  <IconFilePdf className="w-5 h-5 text-slate-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-300">No resume uploaded</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Questions will be based on your job role and experience level. Go back to upload a resume for skill-targeted questions.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="text-xs text-accent-cyan hover:underline font-medium"
                >
                  ← Upload Resume
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                      <IconCheck className="w-3.5 h-3.5 text-emerald-400" /> Resume Uploaded {resumeFileName ? `(${resumeFileName})` : ''}
                    </span>
                    <span className="text-[10px] text-accent-cyan px-2 py-0.5 rounded-full bg-accent-cyan/10 border border-accent-cyan/30">
                      {detectedSkills.length} skills detected
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={selectAllSkills}
                      className="text-[11px] text-accent-cyan hover:underline font-medium"
                    >
                      Select All
                    </button>
                    <span className="text-slate-600">•</span>
                    <button
                      type="button"
                      onClick={clearAllSkills}
                      className="text-[11px] text-slate-400 hover:text-slate-200 hover:underline font-medium"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {/* Skill Chips Grid */}
                <div className="flex flex-wrap gap-2.5">
                  {detectedSkills.map((skill) => (
                    <SkillChip
                      key={skill}
                      skill={skill}
                      selected={selectedSkills.includes(skill)}
                      onToggle={toggleSkill}
                    />
                  ))}
                </div>

                {/* Selection Summary */}
                <div className={`p-4 rounded-xl border transition-all ${
                  selectedSkills.length > 0
                    ? 'bg-accent-cyan/5 border-accent-cyan/20'
                    : 'bg-rose-500/5 border-rose-500/20'
                }`}>
                  {selectedSkills.length > 0 ? (
                    <div className="space-y-1.5">
                      <p className="text-xs font-bold text-accent-cyan flex items-center gap-1.5">
                        <IconCheck className="w-3.5 h-3.5" />
                        Interview will focus on: {selectedSkills.join(', ')}
                      </p>
                      <p className="text-[11px] text-slate-400">
                        The AI interviewer will generate questions specifically targeting{' '}
                        {selectedSkills.length === 1
                          ? `${selectedSkills[0]}.`
                          : `these ${selectedSkills.length} skills. Integration questions may appear when appropriate.`}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-rose-300 font-medium">
                      ⚠ Select at least one skill to continue. The AI needs a focus area to generate targeted questions.
                    </p>
                  )}
                </div>

                {errors.skills && (
                  <p className="text-rose-400 text-xs font-medium">{errors.skills}</p>
                )}
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-white/[0.06]">
              <Button type="button" variant="secondary" onClick={handlePrevStep}>
                Back
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleNextStep}
                icon={IconArrowRight}
                iconPosition="right"
                disabled={detectedSkills.length > 0 && selectedSkills.length === 0}
                className={`px-6 py-2.5 rounded-xl ${
                  detectedSkills.length > 0 && selectedSkills.length === 0
                    ? 'opacity-50 cursor-not-allowed'
                    : ''
                }`}
              >
                Continue to Language Selection
              </Button>
            </div>
          </GlassCard>
        )}

        {/* ─── STEP 3: LANGUAGE SELECTION & ROLE ─── */}
        {currentStep === 3 && (
          <GlassCard className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white">Step 3: Language & Target Role</h2>
              <p className="text-xs text-slate-400 mt-1">
                Select your preferred interview language and confirm your target job role.
              </p>
            </div>

            {/* Language Selection */}
            <OptionGroup
              label="Which language would you like your interview questions in?"
              description="Question text & narration will follow your chosen language while preserving technical terms (Python, REST API, SQL, Docker, etc.)."
              options={LANGUAGES}
              value={form.interview_language}
              onChange={handleSelect}
              fieldName="interview_language"
            />

            {form.interview_language === 'Other' && (
              <div className="space-y-2 pt-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Enter Custom Language Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Spanish, German, French, Japanese"
                  value={form.custom_language}
                  onChange={(e) => setForm((prev) => ({ ...prev, custom_language: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-xl glass-input text-sm"
                />
              </div>
            )}

            <div className="border-t border-white/[0.06]" />

            {/* Target Job Role */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Target Job Role
                </label>
                <button
                  type="button"
                  onClick={() => setIsEditingRole(!isEditingRole)}
                  className="text-xs text-accent-cyan font-medium hover:underline"
                >
                  {isEditingRole ? 'Done' : 'Edit Role'}
                </button>
              </div>

              {isEditingRole ? (
                <input
                  id="input-job-role"
                  type="text"
                  placeholder="e.g. Backend Developer, Data Scientist, Full Stack Lead"
                  value={form.job_role}
                  onChange={(e) => {
                    setForm((prev) => ({ ...prev, job_role: e.target.value }));
                    setErrors((prev) => ({ ...prev, job_role: '' }));
                  }}
                  className="w-full px-4 py-2.5 rounded-xl glass-input text-sm"
                />
              ) : (
                <div className="p-3.5 rounded-xl glass-panel flex items-center justify-between border-white/10">
                  <div>
                    <p className="text-xs text-slate-400">Target Role:</p>
                    <p className="text-sm font-bold text-white">{form.job_role}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsEditingRole(true)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 hover:text-white border border-white/10"
                  >
                    Edit
                  </button>
                </div>
              )}
              {errors.job_role && <p className="text-rose-400 text-xs font-medium">{errors.job_role}</p>}
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-white/[0.06]">
              <Button type="button" variant="secondary" onClick={handlePrevStep}>
                Back
              </Button>
              <Button type="button" variant="primary" onClick={handleNextStep} icon={IconArrowRight} iconPosition="right">
                Continue to Options
              </Button>
            </div>
          </GlassCard>
        )}

        {/* ─── STEP 4: SETUP OPTIONS ─── */}
        {currentStep === 4 && (
          <GlassCard className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white">Step 4: Setup Options</h2>
              <p className="text-xs text-slate-400 mt-1">
                Customize interview domain, difficulty, and total question count.
              </p>
            </div>

            <OptionGroup
              label="Interview Domain / Type"
              options={INTERVIEW_TYPES}
              value={form.interview_type}
              onChange={handleSelect}
              fieldName="interview_type"
            />

            <div className="border-t border-white/[0.06]" />

            <OptionGroup
              label="Experience Level"
              options={EXPERIENCE_LEVELS}
              value={form.experience_level}
              onChange={handleSelect}
              fieldName="experience_level"
            />

            <div className="border-t border-white/[0.06]" />

            <OptionGroup
              label="Difficulty Level"
              options={DIFFICULTIES}
              value={form.difficulty}
              onChange={handleSelect}
              fieldName="difficulty"
            />

            <div className="border-t border-white/[0.06]" />

            <OptionGroup
              label="Question Count"
              options={QUESTION_COUNTS}
              value={form.question_count}
              onChange={handleSelect}
              fieldName="question_count"
            />

            <div className="border-t border-white/[0.06]" />

            {/* Optional Job Description */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Optional Target Job Description
              </label>
              <textarea
                maxLength={2000}
                placeholder="Paste job posting details to calibrate questions..."
                value={form.job_description}
                onChange={(e) => setForm((prev) => ({ ...prev, job_description: e.target.value }))}
                className="w-full px-4 py-3 rounded-xl glass-input text-xs leading-relaxed h-24 resize-none"
              />
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-white/[0.06]">
              <Button type="button" variant="secondary" onClick={handlePrevStep}>
                Back
              </Button>
              <Button type="button" variant="primary" onClick={handleNextStep} icon={IconArrowRight} iconPosition="right">
                Review & Start
              </Button>
            </div>
          </GlassCard>
        )}

        {/* ─── STEP 5: REVIEW & START ─── */}
        {currentStep === 5 && (
          <GlassCard className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Step 5: Review & Launch Interview</span>
                <span className="p-1 rounded-lg bg-primary-600/20 text-primary-400">
                  <IconSparkles className="w-4 h-4" />
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Confirm your interview configuration before starting your AI session.
              </p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl glass-panel space-y-1.5 border-white/10">
                <span className="text-[11px] text-slate-400 uppercase font-mono">Job Role</span>
                <p className="text-sm font-bold text-white">{form.job_role}</p>
              </div>

              <div className="p-4 rounded-xl glass-panel space-y-1.5 border-white/10">
                <span className="text-[11px] text-slate-400 uppercase font-mono">Language</span>
                <p className="text-sm font-bold text-accent-cyan">
                  {form.interview_language === 'Other' ? form.custom_language || 'Other' : form.interview_language}
                </p>
              </div>

              <div className="p-4 rounded-xl glass-panel space-y-1.5 border-white/10">
                <span className="text-[11px] text-slate-400 uppercase font-mono">Domain & Level</span>
                <p className="text-sm font-bold text-white">
                  {form.interview_type} • {form.experience_level}
                </p>
              </div>

              <div className="p-4 rounded-xl glass-panel space-y-1.5 border-white/10">
                <span className="text-[11px] text-slate-400 uppercase font-mono">Difficulty & Questions</span>
                <p className="text-sm font-bold text-white">
                  {form.difficulty} • {form.question_count} Questions
                </p>
              </div>
            </div>

            {/* Skill Focus — highlighted separately */}
            {selectedSkills.length > 0 && (
              <div className="p-4 rounded-xl border border-accent-cyan/25 bg-accent-cyan/5 space-y-2">
                <div className="flex items-center gap-2">
                  <IconCheck className="w-3.5 h-3.5 text-accent-cyan flex-shrink-0" />
                  <span className="text-xs font-bold text-accent-cyan uppercase tracking-wider">
                    AI Interview Focus ({selectedSkills.length} {selectedSkills.length === 1 ? 'skill' : 'skills'})
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedSkills.map((s) => (
                    <span
                      key={s}
                      className="px-3 py-1 rounded-lg text-xs font-bold bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
                    >
                      ✓ {s}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400">
                  Questions will be generated specifically about these skills.
                </p>
              </div>
            )}

            {/* All Detected Skills (dimmed) */}
            {detectedSkills.length > 0 && selectedSkills.length < detectedSkills.length && (
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  All Resume Skills ({detectedSkills.length})
                </span>
                <div className="flex flex-wrap gap-2">
                  {detectedSkills.map((s) => (
                    <span
                      key={s}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                        selectedSkills.includes(s)
                          ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/30'
                          : 'bg-white/[0.03] text-slate-500 border-white/[0.06]'
                      }`}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {apiError && (
              <div className="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-white/[0.06]">
              <Button type="button" variant="secondary" onClick={handlePrevStep}>
                Back
              </Button>
              <Button
                id="btn-create-interview"
                type="submit"
                loading={loading}
                icon={IconArrowRight}
                iconPosition="right"
                variant="primary"
                className="px-8 py-3 rounded-xl shadow-glow-primary"
              >
                Launch Interview Studio
              </Button>
            </div>
          </GlassCard>
        )}
      </form>
    </div>
  );
}
