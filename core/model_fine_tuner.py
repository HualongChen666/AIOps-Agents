# -*- coding: utf-8 -*-
"""
Model Fine-tuning Support (Phase 3)
Enterprise-grade model fine-tuning system with advanced training capabilities
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class FineTuningMethod(Enum):
    """Fine-tuning method types"""

    FULL_FINE_TUNING = "full_fine_tuning"
    LORA = "lora"  # Low-Rank Adaptation
    QLORA = "qlora"  # Quantized LoRA
    ADAPTER = "adapter"
    PREFIX_TUNING = "prefix_tuning"
    PROMPT_TUNING = "prompt_tuning"


class TrainingStatus(Enum):
    """Training status"""

    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SAVED = "saved"


class ModelType(Enum):
    """Model type"""

    LANGUAGE_MODEL = "language_model"
    VISION_MODEL = "vision_model"
    MULTIMODAL_MODEL = "multimodal_model"
    EMBEDDING_MODEL = "embedding_model"


@dataclass
class TrainingConfig:
    """Training configuration"""

    model_name: str
    model_type: ModelType
    fine_tuning_method: FineTuningMethod
    learning_rate: float = 0.0001
    batch_size: int = 8
    num_epochs: int = 3
    warmup_steps: int = 100
    weight_decay: float = 0.01
    max_sequence_length: int = 512
    gradient_accumulation_steps: int = 1
    fp16: bool = False
    bf16: bool = True
    gradient_checkpointing: bool = True
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    max_grad_norm: float = 1.0
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingDataset:
    """Training dataset configuration"""

    dataset_id: str
    dataset_path: str
    dataset_type: str = "json"
    train_split: float = 0.8
    validation_split: float = 0.1
    test_split: float = 0.1
    preprocessing_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingProgress:
    """Training progress information"""

    job_id: str
    status: TrainingStatus
    current_epoch: int = 0
    total_epochs: int = 0
    current_step: int = 0
    total_steps: int = 0
    training_loss: float = 0.0
    validation_loss: float = 0.0
    learning_rate: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelFineTuner:
    """Enterprise-grade model fine-tuning system"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize model fine-tuner

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Training jobs
        self.training_jobs: Dict[str, TrainingProgress] = {}
        self.job_configs: Dict[str, TrainingConfig] = {}
        self.job_datasets: Dict[str, TrainingDataset] = {}

        # Model storage
        self.models_dir = Path(self.config.get("models_dir", "./models"))
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Checkpoint storage
        self.checkpoints_dir = Path(self.config.get("checkpoints_dir", "./checkpoints"))
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Training configuration
        self.max_concurrent_jobs = self.config.get("max_concurrent_jobs", 2)
        self.device = self.config.get("device", "cuda")

        # Statistics
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0

        # Per-job runtime state (loaded model/tokenizer)
        self._training_state: Dict[str, Dict[str, Any]] = {}

        # Estimated optimizer steps per epoch (used for progress reporting)
        self.steps_per_epoch = int(self.config.get("steps_per_epoch", 1000))

        logger.info("Model fine-tuner initialized")

    async def start_fine_tuning(
        self, training_config: TrainingConfig, training_dataset: TrainingDataset
    ) -> str:
        """
        Start fine-tuning job

        Args:
            training_config: Training configuration
            training_dataset: Training dataset

        Returns:
            Job ID
        """
        job_id = f"ft_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self.total_jobs}"

        # Create training progress
        progress = TrainingProgress(
            job_id=job_id,
            status=TrainingStatus.PENDING,
            total_epochs=training_config.num_epochs,
            started_at=datetime.now(timezone.utc),
        )

        self.training_jobs[job_id] = progress
        self.job_configs[job_id] = training_config
        self.job_datasets[job_id] = training_dataset
        self.total_jobs += 1

        logger.info(f"Started fine-tuning job: {job_id}")

        # Start training asynchronously
        asyncio.create_task(self._execute_training(job_id))

        return job_id

    async def _execute_training(self, job_id: str) -> None:
        """
        Execute training job

        Args:
            job_id: Job ID
        """
        if job_id not in self.training_jobs:
            return

        progress = self.training_jobs[job_id]
        config = self.job_configs[job_id]
        dataset = self.job_datasets[job_id]

        try:
            # Update status to preparing
            progress.status = TrainingStatus.PREPARING

            # Prepare training
            await self._prepare_training(job_id, config, dataset)

            # Update status to training
            progress.status = TrainingStatus.TRAINING
            progress.total_steps = config.num_epochs * self.steps_per_epoch

            # Run the real training loop
            await self._train_model(job_id, config)

            # Update status to completed
            progress.status = TrainingStatus.COMPLETED
            progress.completed_at = datetime.now(timezone.utc)
            self.completed_jobs += 1

            logger.info(f"Fine-tuning job completed: {job_id}")

        except Exception as e:
            progress.status = TrainingStatus.FAILED
            progress.error_message = str(e)
            progress.completed_at = datetime.now(timezone.utc)
            self.failed_jobs += 1
            logger.error(f"Fine-tuning job failed: {job_id}, error: {e}")

    def _load_base_model(self, config: TrainingConfig) -> tuple[Any, Any]:
        """Load the base model and tokenizer for fine-tuning.

        Raises:
            RuntimeError: when the ``transformers`` package is unavailable.
        """
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "transformers is required for model fine-tuning; install it to run jobs"
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(config.model_name, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(config.model_name)
        return model, tokenizer

    async def _prepare_training(
        self, job_id: str, config: TrainingConfig, dataset: TrainingDataset
    ) -> None:
        """
        Prepare training resources: validate the dataset and load the base model.

        Args:
            job_id: Job ID
            config: Training configuration
            dataset: Training dataset

        Raises:
            FileNotFoundError: when the dataset path does not exist.
            RuntimeError: when the training stack is unavailable.
        """
        dataset_path = Path(dataset.dataset_path)
        if not dataset_path.exists():
            raise FileNotFoundError(f"training dataset not found: {dataset_path}")

        model, tokenizer = await asyncio.to_thread(self._load_base_model, config)
        self._training_state[job_id] = {"model": model, "tokenizer": tokenizer}
        logger.info(f"Training preparation completed for job: {job_id}")

    def _run_trainer(
        self,
        job_id: str,
        model: Any,
        tokenizer: Any,
        dataset: TrainingDataset,
        config: TrainingConfig,
    ) -> Dict[str, Any]:
        """Run ``transformers.Trainer`` and return the final metrics.

        Raises:
            RuntimeError: when the datasets/transformers stack is unavailable.
        """
        try:
            from datasets import load_dataset
            from transformers import (
                DataCollatorForLanguageModeling,
                Trainer,
                TrainingArguments,
            )
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "datasets and transformers are required to run fine-tuning jobs"
            ) from exc

        raw = load_dataset(dataset.dataset_type, data_files=dataset.dataset_path, split="train")
        text_column = dataset.metadata.get("text_column", "text")
        if text_column not in raw.column_names:
            text_column = raw.column_names[0]

        def _tokenize(batch: Dict[str, Any]) -> Dict[str, Any]:
            return tokenizer(
                batch[text_column],
                truncation=True,
                max_length=config.max_sequence_length,
                padding="max_length",
            )

        tokenized = raw.map(_tokenize, batched=True, remove_columns=raw.column_names)

        training_args = TrainingArguments(
            output_dir=str(self.checkpoints_dir / job_id),
            learning_rate=config.learning_rate,
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=config.batch_size,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            warmup_steps=config.warmup_steps,
            weight_decay=config.weight_decay,
            logging_steps=config.logging_steps,
            save_steps=config.save_steps,
            eval_steps=config.eval_steps,
            max_grad_norm=config.max_grad_norm,
            fp16=config.fp16,
            bf16=config.bf16,
            gradient_checkpointing=config.gradient_checkpointing,
            report_to=[],
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized,
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=tokenizer, mlm=False
            ),
        )
        train_output = trainer.train()
        metrics = dict(getattr(train_output, "metrics", {}) or {})
        metrics["global_step"] = trainer.state.global_step
        return metrics

    async def _train_model(self, job_id: str, config: TrainingConfig) -> None:
        """
        Run the real fine-tuning loop, recording the actual loss/metrics.

        Args:
            job_id: Job ID
            config: Training configuration
        """
        state = self._training_state.get(job_id)
        if not state:
            raise RuntimeError(f"model for job {job_id} was not prepared")
        dataset = self.job_datasets[job_id]
        progress = self.training_jobs[job_id]

        metrics = await asyncio.to_thread(
            self._run_trainer,
            job_id,
            state["model"],
            state["tokenizer"],
            dataset,
            config,
        )

        progress.current_epoch = config.num_epochs
        progress.current_step = int(metrics.get("global_step", 0))
        if "train_loss" in metrics:
            progress.training_loss = float(metrics["train_loss"])
        progress.metrics = {
            k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))
        }
        if progress.started_at is not None:
            progress.elapsed_time = (
                datetime.now(timezone.utc) - progress.started_at
            ).total_seconds()

        await self._save_checkpoint(job_id, config.num_epochs)

    async def _save_checkpoint(self, job_id: str, epoch: int) -> None:
        """
        Save the fine-tuned model checkpoint.

        Args:
            job_id: Job ID
            epoch: Current epoch
        """
        checkpoint_path = self.checkpoints_dir / job_id / f"checkpoint_epoch_{epoch}"
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        state = self._training_state.get(job_id)
        model = state.get("model") if state else None
        tokenizer = state.get("tokenizer") if state else None
        if model is None:
            raise RuntimeError(f"cannot save checkpoint for job {job_id}: model not loaded")

        saved = await asyncio.to_thread(model.save_pretrained, str(checkpoint_path))
        if tokenizer is not None:
            await asyncio.to_thread(tokenizer.save_pretrained, str(checkpoint_path))
        logger.info(f"Checkpoint saved for job {job_id}, epoch {epoch} at {saved or checkpoint_path}")

    def get_training_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get training progress

        Args:
            job_id: Job ID

        Returns:
            Training progress dictionary
        """
        if job_id not in self.training_jobs:
            return None

        progress = self.training_jobs[job_id]

        return {
            "job_id": progress.job_id,
            "status": progress.status.value,
            "current_epoch": progress.current_epoch,
            "total_epochs": progress.total_epochs,
            "current_step": progress.current_step,
            "total_steps": progress.total_steps,
            "training_loss": progress.training_loss,
            "validation_loss": progress.validation_loss,
            "learning_rate": progress.learning_rate,
            "elapsed_time": progress.elapsed_time,
            "estimated_remaining_time": progress.estimated_remaining_time,
            "metrics": progress.metrics,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "error_message": progress.error_message,
        }

    async def cancel_training(self, job_id: str) -> bool:
        """
        Cancel training job

        Args:
            job_id: Job ID

        Returns:
            Success status
        """
        if job_id not in self.training_jobs:
            return False

        progress = self.training_jobs[job_id]

        if progress.status in (
            TrainingStatus.PENDING,
            TrainingStatus.PREPARING,
            TrainingStatus.TRAINING,
        ):
            progress.status = TrainingStatus.CANCELLED
            progress.completed_at = datetime.now(timezone.utc)
            logger.info(f"Training job cancelled: {job_id}")
            return True

        return False

    def list_training_jobs(self, status: Optional[TrainingStatus] = None) -> List[Dict[str, Any]]:
        """
        List training jobs

        Args:
            status: Filter by status (optional)

        Returns:
            List of job information
        """
        jobs = []

        for job_id, progress in self.training_jobs.items():
            if status and progress.status != status:
                continue

            jobs.append(
                {
                    "job_id": job_id,
                    "status": progress.status.value,
                    "model_name": self.job_configs[job_id].model_name,
                    "started_at": progress.started_at.isoformat() if progress.started_at else None,
                    "completed_at": (
                        progress.completed_at.isoformat() if progress.completed_at else None
                    ),
                }
            )

        return jobs

    def get_statistics(self) -> Dict[str, Any]:
        """Get training statistics"""
        return {
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "active_jobs": len(
                [
                    j
                    for j in self.training_jobs.values()
                    if j.status in (TrainingStatus.PREPARING, TrainingStatus.TRAINING)
                ]
            ),
            "success_rate": self.completed_jobs / self.total_jobs if self.total_jobs > 0 else 0.0,
        }

    async def export_model(self, job_id: str, export_format: str = "pytorch") -> Optional[str]:
        """
        Export fine-tuned model

        Args:
            job_id: Job ID
            export_format: Export format (pytorch, onnx, tensorflow)

        Returns:
            Export path or None
        """
        if job_id not in self.training_jobs:
            return None

        progress = self.training_jobs[job_id]

        if progress.status != TrainingStatus.COMPLETED:
            return None

        # In real implementation, would export actual model
        export_path = self.models_dir / job_id / f"model.{export_format}"
        export_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Model exported to: {export_path}")
        return str(export_path)


def get_model_fine_tuner(config: Optional[Dict[str, Any]] = None) -> ModelFineTuner:
    """
    Factory function to get model fine-tuner instance

    Args:
        config: Optional configuration dictionary

    Returns:
        ModelFineTuner: Fine-tuner instance
    """
    return ModelFineTuner(config)
