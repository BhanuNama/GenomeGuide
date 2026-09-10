import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function DnaCanvas({ height = 280, interactive = true, className = '' }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Scene & Camera
    const scene = new THREE.Scene();
    const width = container.clientWidth || 300;
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 32;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Group for DNA
    const dnaGroup = new THREE.Group();
    scene.add(dnaGroup);

    // Colors
    const sageColor = new THREE.Color(0x4e8860);
    const emeraldColor = new THREE.Color(0x22c55e);
    const goldColor = new THREE.Color(0xeab308);
    const cyanColor = new THREE.Color(0x38bdf8);

    // Helix Configuration
    const numPairs = 38;
    const radius = 5.6;
    const heightStep = 0.88;
    const angleStep = 0.32;

    const sphereGeom = new THREE.SphereGeometry(0.4, 18, 18);
    const matBackboneA = new THREE.MeshStandardMaterial({
      color: emeraldColor,
      roughness: 0.25,
      metalness: 0.3,
      emissive: 0x164e2a,
      emissiveIntensity: 0.45,
    });
    const matBackboneB = new THREE.MeshStandardMaterial({
      color: cyanColor,
      roughness: 0.25,
      metalness: 0.3,
      emissive: 0x0c4a6e,
      emissiveIntensity: 0.45,
    });
    const matRungA = new THREE.MeshStandardMaterial({
      color: sageColor,
      roughness: 0.35,
      metalness: 0.15,
      emissive: 0x1f3f2a,
      emissiveIntensity: 0.25,
    });
    const matRungB = new THREE.MeshStandardMaterial({
      color: goldColor,
      roughness: 0.35,
      metalness: 0.15,
      emissive: 0x3f3010,
      emissiveIntensity: 0.25,
    });

    const yOffset = (numPairs * heightStep) / 2;
    const nodes = [];

    for (let i = 0; i < numPairs; i++) {
      const angle = i * angleStep;
      const baseY = i * heightStep - yOffset;

      const x1 = Math.cos(angle) * radius;
      const z1 = Math.sin(angle) * radius;
      const sphere1 = new THREE.Mesh(sphereGeom, matBackboneA);
      sphere1.position.set(x1, baseY, z1);
      dnaGroup.add(sphere1);

      const x2 = Math.cos(angle + Math.PI) * radius;
      const z2 = Math.sin(angle + Math.PI) * radius;
      const sphere2 = new THREE.Mesh(sphereGeom, matBackboneB);
      sphere2.position.set(x2, baseY, z2);
      dnaGroup.add(sphere2);

      // Connecting nucleotide rung
      const p1 = new THREE.Vector3(x1, baseY, z1);
      const p2 = new THREE.Vector3(x2, baseY, z2);
      const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      const distance = p1.distanceTo(p2);

      const rungGeom = new THREE.CylinderGeometry(0.12, 0.12, distance * 0.96, 8);
      const rungMat = i % 2 === 0 ? matRungA : matRungB;
      const rung = new THREE.Mesh(rungGeom, rungMat);

      rung.position.copy(midPoint);
      rung.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        new THREE.Vector3().subVectors(p2, p1).normalize()
      );
      dnaGroup.add(rung);

      nodes.push({ sphere1, sphere2, rung, baseY, angle });
    }

    // Ambient floating genomic particles
    const particleCount = 85;
    const particleGeom = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);

    for (let p = 0; p < particleCount * 3; p += 3) {
      particlePos[p] = (Math.random() - 0.5) * 44;
      particlePos[p + 1] = (Math.random() - 0.5) * 44;
      particlePos[p + 2] = (Math.random() - 0.5) * 24;
    }

    particleGeom.setAttribute('position', new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x6ba07a,
      size: 0.38,
      transparent: true,
      opacity: 0.7,
    });
    const particles = new THREE.Points(particleGeom, particleMat);
    scene.add(particles);

    // Orbiting Dynamic Point Lights
    const lightA = new THREE.PointLight(0x22c55e, 2.2, 50);
    const lightB = new THREE.PointLight(0x38bdf8, 2.2, 50);
    scene.add(lightA);
    scene.add(lightB);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(15, 25, 20);
    scene.add(dirLight1);

    // Dynamic initial tilt
    dnaGroup.rotation.z = 0.3;

    // Interaction state: Drag to Orbit + Hover Tilt + Wheel Zoom
    let isDragging = false;
    let prevMousePos = { x: 0, y: 0 };
    let dragVelocity = { x: 0, y: 0 };
    let mouseHover = { x: 0, y: 0 };

    const onMouseDown = (e) => {
      if (!interactive) return;
      isDragging = true;
      prevMousePos = { x: e.clientX, y: e.clientY };
      container.style.cursor = 'grabbing';
    };

    const onMouseMove = (e) => {
      if (!interactive) return;
      const rect = container.getBoundingClientRect();
      mouseHover.x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      mouseHover.y = -((e.clientY - rect.top) / rect.height - 0.5) * 2;

      if (isDragging) {
        const deltaX = e.clientX - prevMousePos.x;
        const deltaY = e.clientY - prevMousePos.y;
        dragVelocity.x = deltaX * 0.008;
        dragVelocity.y = deltaY * 0.008;
        prevMousePos = { x: e.clientX, y: e.clientY };
      }
    };

    const onMouseUp = () => {
      isDragging = false;
      if (container) container.style.cursor = 'grab';
    };

    const onWheel = (e) => {
      if (!interactive) return;
      e.preventDefault();
      camera.position.z += e.deltaY * 0.02;
      camera.position.z = Math.max(18, Math.min(52, camera.position.z));
    };

    if (interactive) {
      container.addEventListener('mousedown', onMouseDown);
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
      container.addEventListener('wheel', onWheel, { passive: false });
    }

    // Animation loop
    let animId;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Drag inertia damping
      dnaGroup.rotation.y += dragVelocity.x;
      dnaGroup.rotation.x += dragVelocity.y;
      dragVelocity.x *= 0.94;
      dragVelocity.y *= 0.94;

      // Continuous gentle rotation
      dnaGroup.rotation.y += 0.009;
      particles.rotation.y += 0.002;

      // Subtle biological breathing wave motion
      for (let i = 0; i < nodes.length; i++) {
        const wave = Math.sin(elapsed * 2.2 + i * 0.22) * 0.2;
        const n = nodes[i];
        n.sphere1.position.y = n.baseY + wave;
        n.sphere2.position.y = n.baseY - wave;
      }

      // Orbit dynamic colored lights
      lightA.position.set(
        Math.cos(elapsed * 1.2) * 14,
        Math.sin(elapsed * 0.8) * 10,
        Math.sin(elapsed * 1.2) * 14
      );
      lightB.position.set(
        Math.cos(elapsed * 1.2 + Math.PI) * 14,
        Math.sin(elapsed * 0.8 + Math.PI) * 10,
        Math.sin(elapsed * 1.2 + Math.PI) * 14
      );

      // Mouse hover parallax tilt
      if (!isDragging) {
        const targetX = mouseHover.y * 0.35;
        dnaGroup.rotation.x += (targetX - dnaGroup.rotation.x) * 0.04;
      }

      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      camera.aspect = newWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, height);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      if (interactive) {
        container.removeEventListener('mousedown', onMouseDown);
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        container.removeEventListener('wheel', onWheel);
      }
      renderer.dispose();
      sphereGeom.dispose();
      particleGeom.dispose();
      matBackboneA.dispose();
      matBackboneB.dispose();
      matRungA.dispose();
      matRungB.dispose();
      particleMat.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [height, interactive]);

  return (
    <div
      ref={mountRef}
      className={className}
      style={{
        width: '100%',
        height: `${height}px`,
        position: 'relative',
        cursor: interactive ? 'grab' : 'default',
        overflow: 'hidden',
        userSelect: 'none',
      }}
    />
  );
}
