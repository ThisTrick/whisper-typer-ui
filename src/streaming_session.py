"""Streaming transcription session manager for Whisper Typer UI."""

import logging
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue
from typing import Callable, Optional
import threading

from audio_recorder import AudioChunk
from utils import ChunkTranscriptionResult


logger = logging.getLogger(__name__)


class StreamingSession:
    """Manages parallel transcription of audio chunks with ordered text insertion.
    
    Uses a ThreadPoolExecutor with 3 workers to transcribe chunks in parallel while
    maintaining correct text order through sequence numbers.
    """
    
    def __init__(
        self,
        transcribe_fn: Callable[[AudioChunk], ChunkTranscriptionResult],
        insert_text_fn: Callable[[str], None],
        on_error: Callable[[Exception], None]
    ):
        """Initialize streaming session.
        
        Args:
            transcribe_fn: Function to transcribe a single chunk (from Transcriber)
            insert_text_fn: Function to insert text at cursor (from TextInserter)
            on_error: Callback for any chunk transcription error
        """
        self._transcribe_fn = transcribe_fn
        self._insert_text_fn = insert_text_fn
        self._on_error = on_error
        
        # Thread pool for parallel transcription
        self._executor = ThreadPoolExecutor(max_workers=3)
        
        # Ordered insertion buffer: {sequence: ChunkTranscriptionResult}
        self._completed_chunks: dict[int, ChunkTranscriptionResult] = {}
        
        # Next expected sequence number for insertion
        self._next_insert_sequence: int = 0
        
        # Track active futures for cleanup
        self._active_futures: list[Future] = []
        
        # Error flag to cancel remaining work
        self._has_error: bool = False
        
        # Lock for thread-safe access to _completed_chunks and _next_insert_sequence
        self._lock = threading.Lock()
    
    def submit_chunk(self, chunk: AudioChunk) -> None:
        """Submit an audio chunk for parallel transcription.
        
        Args:
            chunk: AudioChunk with data, sequence, and start_time
            
        Side Effects:
            Spawns worker thread to transcribe chunk
        """
        if self._has_error:
            return  # Don't submit new work if session has error
        
        logger.info(f"[CHUNK {chunk.sequence}] Submitted to transcription queue (worker pool)")
        future = self._executor.submit(self._worker_thread, chunk)
        future.add_done_callback(self._on_chunk_complete)
        self._active_futures.append(future)
    
    def _worker_thread(self, chunk: AudioChunk) -> ChunkTranscriptionResult:
        """Worker function to transcribe a single chunk.
        
        Args:
            chunk: AudioChunk to transcribe
            
        Returns:
            ChunkTranscriptionResult with sequence, text, and optional error
        """
        logger.info(f"[CHUNK {chunk.sequence}] Worker started transcription...")
        try:
            result = self._transcribe_fn(chunk)
            logger.info(f"[CHUNK {chunk.sequence}] Worker finished transcription: {len(result.text)} chars")
            return result
        except Exception as e:
            # Return error result instead of raising
            logger.error(f"[CHUNK {chunk.sequence}] Worker error: {e}")
            return ChunkTranscriptionResult(
                sequence=chunk.sequence,
                text="",
                error=str(e)
            )
    
    def _on_chunk_complete(self, future: Future) -> None:
        """Callback when a chunk transcription completes.
        
        Args:
            future: Completed Future containing ChunkTranscriptionResult
            
        Side Effects:
            - Stores result in _completed_chunks
            - Inserts text if sequence is next expected
            - Calls _on_error if chunk has error
        """
        try:
            result = future.result()
            
            # Check for chunk-level error
            if result.error:
                self._has_error = True
                self._on_error(Exception(f"Chunk {result.sequence} error: {result.error}"))
                return
            
            logger.info(f"[CHUNK {result.sequence}] Transcription complete: {len(result.text)} characters")
            
            # Store completed chunk and insert text in thread-safe manner
            with self._lock:
                self._completed_chunks[result.sequence] = result
                
                # Insert all consecutive completed chunks
                while self._next_insert_sequence in self._completed_chunks:
                    chunk_result = self._completed_chunks.pop(self._next_insert_sequence)
                    if chunk_result.text and not chunk_result.error:  # Only insert non-empty text
                        logger.info(f"[CHUNK {chunk_result.sequence}] Inserting text now")
                        self._insert_text_fn(chunk_result.text)
                    self._next_insert_sequence += 1
                
        except Exception as e:
            self._has_error = True
            self._on_error(e)
    
    def finalize_and_insert(self) -> None:
        """Wait for all pending chunks and insert remaining text.
        
        Blocks until all submitted chunks complete transcription.
        Inserts any remaining buffered text in correct order.
        
        Side Effects:
            - Shuts down executor
            - Inserts all buffered text
        """
        logger.info("[FINALIZE] Waiting for all worker threads to complete...")
        # Shutdown executor and wait for all workers
        self._executor.shutdown(wait=True)
        logger.info("[FINALIZE] All workers completed")
        
        # Insert any remaining buffered chunks in order (thread-safe)
        # Note: Chunks already inserted in _on_chunk_complete were pop()'d from buffer
        with self._lock:
            sequences = sorted(self._completed_chunks.keys())
            if sequences:
                logger.info(f"[FINALIZE] Found {len(sequences)} chunks still in buffer - inserting now")
                
                for seq in sequences:
                    result = self._completed_chunks[seq]
                    if result.text and not result.error:
                        logger.info(f"[CHUNK {seq}] Inserting remaining text ({len(result.text)} chars)")
                        self._insert_text_fn(result.text)
            else:
                logger.info("[FINALIZE] No chunks in buffer - all were inserted during recording")
            
            # Clear the buffer
            self._completed_chunks.clear()
            logger.info("[FINALIZE] Buffer cleared")
