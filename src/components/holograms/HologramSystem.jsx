import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useScroll } from '@react-three/drei';
import * as THREE from 'three';
import { Hologram } from './Hologram';
import { hologramCheckpoints } from './hologramCheckpoints';

const JourneyProgressContext = createContext(null);
const CHECKPOINT_REARM_DISTANCE = 0.02;
const CHECKPOINT_REACHED_EPSILON = 0.002;
const START_REACHED_EPSILON = 0.001;

export function useJourneyProgress() {
  const context = useContext(JourneyProgressContext);
  if (!context) {
    throw new Error('useJourneyProgress must be used inside HologramSystem.');
  }
  return context;
}

export function HologramSystem({ children }) {
  const scroll = useScroll();
  const [activeCheckpoint, setActiveCheckpoint] = useState(null);
  const lockedCheckpoint = useRef(null);
  const hologramIsVisible = useRef(false);
  const completedIds = useRef(new Set());
  const effectiveProgress = useRef(0);
  const previousRawProgress = useRef(0);
  const isReturningToStart = useRef(false);

  const syncScrollTo = useCallback(
    (progress, snapDampedProgress = false) => {
      const axis = scroll.horizontal ? 'scrollLeft' : 'scrollTop';
      const viewportSize = scroll.horizontal ? scroll.el.clientWidth : scroll.el.clientHeight;
      const scrollSize = scroll.horizontal ? scroll.el.scrollWidth : scroll.el.scrollHeight;
      const maxScroll = Math.max(0, scrollSize - viewportSize);
      const pixelPosition = progress * maxScroll;

      if (Math.abs(scroll.el[axis] - pixelPosition) > 0.5) {
        scroll.el[axis] = pixelPosition;
      }
      scroll.scroll.current = progress;
      if (snapDampedProgress) {
        scroll.offset = progress;
        scroll.delta = 0;
      }
    },
    [scroll],
  );

  const completeCheckpoint = useCallback(
    (id) => {
      const checkpoint = lockedCheckpoint.current;
      if (!checkpoint || checkpoint.id !== id) return;

      completedIds.current.add(id);
      syncScrollTo(checkpoint.triggerProgress, true);
      previousRawProgress.current = checkpoint.triggerProgress;
      effectiveProgress.current = checkpoint.triggerProgress;
      lockedCheckpoint.current = null;
      hologramIsVisible.current = false;
      setActiveCheckpoint(null);
    },
    [syncScrollTo],
  );

  const returnToStart = useCallback(() => {
    isReturningToStart.current = true;
    lockedCheckpoint.current = null;
    hologramIsVisible.current = false;
    setActiveCheckpoint(null);
    document.body.style.cursor = 'auto';
    scroll.el.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
  }, [scroll]);

  useFrame(() => {
    if (isReturningToStart.current) {
      const rawProgress = THREE.MathUtils.clamp(scroll.scroll.current, 0, 1);
      const dampedProgress = THREE.MathUtils.clamp(scroll.offset, 0, 1);

      effectiveProgress.current = dampedProgress;
      previousRawProgress.current = rawProgress;

      if (
        rawProgress <= START_REACHED_EPSILON &&
        dampedProgress <= START_REACHED_EPSILON
      ) {
        syncScrollTo(0, true);
        completedIds.current.clear();
        effectiveProgress.current = 0;
        previousRawProgress.current = 0;
        isReturningToStart.current = false;
      }
      return;
    }

    const checkpointLock = lockedCheckpoint.current;
    if (checkpointLock) {
      const reachedCheckpoint = checkpointLock.direction === 'backward'
        ? scroll.offset <= checkpointLock.triggerProgress + CHECKPOINT_REACHED_EPSILON
        : scroll.offset >= checkpointLock.triggerProgress - CHECKPOINT_REACHED_EPSILON;

      syncScrollTo(checkpointLock.triggerProgress, reachedCheckpoint);
      effectiveProgress.current = checkpointLock.direction === 'backward'
        ? Math.max(scroll.offset, checkpointLock.triggerProgress)
        : Math.min(scroll.offset, checkpointLock.triggerProgress);
      previousRawProgress.current = checkpointLock.triggerProgress;

      if (reachedCheckpoint && !hologramIsVisible.current) {
        hologramIsVisible.current = true;
        setActiveCheckpoint(checkpointLock);
      }
      return;
    }

    const rawProgress = THREE.MathUtils.clamp(scroll.scroll.current, 0, 1);
    const dampedProgress = THREE.MathUtils.clamp(scroll.offset, 0, 1);
    const previousRaw = previousRawProgress.current;
    const journeyWasMovingForward = rawProgress > previousRaw;
    const journeyWasMovingBackward = rawProgress < previousRaw;

    // A dismissed checkpoint stays suppressed while the user is still next to
    // it. Once they move away, it becomes available again from either side.
    hologramCheckpoints.forEach((checkpoint) => {
      if (
        completedIds.current.has(checkpoint.id) &&
        Math.abs(rawProgress - checkpoint.triggerProgress) >= CHECKPOINT_REARM_DISTANCE
      ) {
        completedIds.current.delete(checkpoint.id);
      }
    });

    let crossedCheckpoint = null;
    let crossingDirection = null;

    if (journeyWasMovingForward) {
      crossedCheckpoint = hologramCheckpoints.find(
        (checkpoint) =>
          !completedIds.current.has(checkpoint.id) &&
          checkpoint.triggerProgress > previousRaw &&
          checkpoint.triggerProgress <= rawProgress,
      );
      crossingDirection = crossedCheckpoint ? 'forward' : null;
    } else if (journeyWasMovingBackward) {
      for (let index = hologramCheckpoints.length - 1; index >= 0; index -= 1) {
        const checkpoint = hologramCheckpoints[index];
        if (
          !completedIds.current.has(checkpoint.id) &&
          checkpoint.triggerProgress < previousRaw &&
          checkpoint.triggerProgress >= rawProgress
        ) {
          crossedCheckpoint = checkpoint;
          crossingDirection = 'backward';
          break;
        }
      }
    }

    if (crossedCheckpoint) {
      const checkpointLock = { ...crossedCheckpoint, direction: crossingDirection };
      lockedCheckpoint.current = checkpointLock;
      hologramIsVisible.current = false;
      syncScrollTo(crossedCheckpoint.triggerProgress);
      effectiveProgress.current = crossingDirection === 'backward'
        ? Math.max(dampedProgress, crossedCheckpoint.triggerProgress)
        : Math.min(dampedProgress, crossedCheckpoint.triggerProgress);
      previousRawProgress.current = crossedCheckpoint.triggerProgress;
      return;
    }

    effectiveProgress.current = dampedProgress;
    previousRawProgress.current = rawProgress;
  });

  const contextValue = useMemo(
    () => ({ progress: effectiveProgress, returnToStart }),
    [returnToStart],
  );

  return (
    <JourneyProgressContext.Provider value={contextValue}>
      {children}
      {activeCheckpoint && (
        <Hologram checkpoint={activeCheckpoint} onDismissed={completeCheckpoint} />
      )}
    </JourneyProgressContext.Provider>
  );
}
