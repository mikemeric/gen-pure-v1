"""
Analyse des duplications de code - Sprint 6 Étape 2

Identifie:
1. Fichiers obsolètes/orphelins (non importés)
2. Duplications de modèles/schemas
3. Duplications de fonctions similaires
4. Code mort
"""
import os
import re
from pathlib import Path
from collections import defaultdict


def find_imports(root_dir):
    """Trouve tous les imports dans le projet"""
    imports = defaultdict(list)
    
    for root, dirs, files in os.walk(root_dir):
        # Skip pycache
        if '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Find "from X import Y"
                    from_imports = re.findall(r'from\s+([\w.]+)\s+import', content)
                    
                    # Find "import X"
                    direct_imports = re.findall(r'^import\s+([\w.]+)', content, re.MULTILINE)
                    
                    for imp in from_imports + direct_imports:
                        imports[imp].append(filepath)
                
                except Exception as e:
                    print(f"  Error reading {filepath}: {e}")
    
    return imports


def find_orphan_files(root_dir):
    """Trouve les fichiers Python jamais importés"""
    print("\n🔍 RECHERCHE DE FICHIERS ORPHELINS")
    print("=" * 60)
    
    # Get all imports
    imports = find_imports(root_dir)
    
    # Get all Python files
    all_files = []
    for root, dirs, files in os.walk(root_dir):
        if '__pycache__' in root or 'tests' in root:
            continue
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                # Convert to module path
                rel_path = os.path.relpath(filepath, root_dir)
                module_path = rel_path.replace('/', '.').replace('\\', '.')[:-3]
                all_files.append((filepath, module_path))
    
    # Find orphans
    orphans = []
    for filepath, module_path in all_files:
        # Check if this module is imported anywhere
        is_imported = False
        
        for imported_module in imports.keys():
            if module_path in imported_module or imported_module in module_path:
                is_imported = True
                break
        
        if not is_imported:
            orphans.append((filepath, module_path))
    
    if orphans:
        print(f"\n❌ {len(orphans)} fichier(s) orphelin(s) trouvé(s):\n")
        for filepath, module in orphans:
            size = os.path.getsize(filepath)
            print(f"  • {module}")
            print(f"    Path: {filepath}")
            print(f"    Size: {size} bytes")
            print()
    else:
        print("\n✅ Aucun fichier orphelin trouvé")
    
    return orphans


def find_duplicate_classes(root_dir):
    """Trouve les classes dupliquées"""
    print("\n🔍 RECHERCHE DE CLASSES DUPLIQUÉES")
    print("=" * 60)
    
    classes = defaultdict(list)
    
    for root, dirs, files in os.walk(root_dir):
        if '__pycache__' in root or 'tests' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Find class definitions
                    class_defs = re.findall(r'class\s+(\w+)', content)
                    
                    for class_name in class_defs:
                        classes[class_name].append(filepath)
                
                except Exception as e:
                    pass
    
    # Find duplicates
    duplicates = {k: v for k, v in classes.items() if len(v) > 1}
    
    if duplicates:
        print(f"\n❌ {len(duplicates)} classe(s) dupliquée(s):\n")
        for class_name, files in sorted(duplicates.items()):
            print(f"  • {class_name} ({len(files)} occurrences)")
            for f in files:
                print(f"    - {f}")
            print()
    else:
        print("\n✅ Aucune classe dupliquée trouvée")
    
    return duplicates


def analyze_file_sizes(root_dir):
    """Analyse la taille des fichiers"""
    print("\n📊 ANALYSE TAILLE DES FICHIERS")
    print("=" * 60)
    
    files_by_size = []
    
    for root, dirs, files in os.walk(root_dir):
        if '__pycache__' in root or 'tests' in root:
            continue
        
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                size = os.path.getsize(filepath)
                
                with open(filepath, 'r') as f:
                    lines = len(f.readlines())
                
                files_by_size.append((filepath, size, lines))
    
    # Sort by size
    files_by_size.sort(key=lambda x: x[1], reverse=True)
    
    print("\n📈 Top 10 fichiers les plus gros:\n")
    for filepath, size, lines in files_by_size[:10]:
        kb = size / 1024
        print(f"  • {os.path.basename(filepath)}")
        print(f"    Path: {filepath}")
        print(f"    Size: {kb:.1f} KB ({lines} lignes)")
        print()
    
    return files_by_size


def check_model_duplications(root_dir):
    """Vérifie les duplications de modèles"""
    print("\n🔍 VÉRIFICATION DUPLICATIONS MODÈLES")
    print("=" * 60)
    
    model_files = [
        'core/models.py',
        'api/schemas/detection.py',
        'infrastructure/database/models.py'
    ]
    
    for model_file in model_files:
        full_path = os.path.join(root_dir, model_file)
        
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                lines = len(f.readlines())
            
            # Check if imported
            imports = find_imports(root_dir)
            module_name = model_file.replace('/', '.').replace('\\', '.')[:-3]
            
            is_imported = any(module_name in imp for imp in imports.keys())
            
            status = "✅ Utilisé" if is_imported else "❌ ORPHELIN"
            print(f"\n  {model_file}")
            print(f"    Lignes: {lines}")
            print(f"    Status: {status}")
            
            if not is_imported:
                print(f"    → PEUT ÊTRE SUPPRIMÉ")


def generate_refactoring_plan(orphans, duplicates):
    """Génère un plan de refactoring"""
    print("\n" + "=" * 60)
    print("📋 PLAN DE REFACTORING")
    print("=" * 60)
    
    actions = []
    
    # Orphan files
    if orphans:
        print(f"\n1. SUPPRIMER FICHIERS ORPHELINS ({len(orphans)} fichiers)")
        for filepath, module in orphans:
            print(f"   • git rm {filepath}")
            actions.append(('delete', filepath))
    
    # Duplicate classes
    if duplicates:
        print(f"\n2. RÉSOUDRE CLASSES DUPLIQUÉES ({len(duplicates)} classes)")
        
        priority_duplicates = {
            'DetectionResult': 'Utiliser api/schemas/detection.py (Pydantic)',
            'DetectionResponse': 'Unifier avec DetectionResult',
            'User': 'Utiliser infrastructure/database/models.py (SQLAlchemy)',
        }
        
        for class_name, solution in priority_duplicates.items():
            if class_name in duplicates:
                print(f"   • {class_name}: {solution}")
                actions.append(('merge', class_name))
    
    # Model files
    print("\n3. CONSOLIDER MODÈLES")
    print("   • Supprimer core/models.py (obsolète)")
    print("   • Garder api/schemas/ (Pydantic pour API)")
    print("   • Garder infrastructure/database/models.py (SQLAlchemy pour DB)")
    actions.append(('delete', 'core/models.py'))
    
    print("\n" + "=" * 60)
    print(f"📊 Total actions: {len(actions)}")
    print("=" * 60)
    
    return actions


if __name__ == "__main__":
    print("=" * 60)
    print("ANALYSE DUPLICATIONS - SPRINT 6 ÉTAPE 2")
    print("=" * 60)
    
    root_dir = "/home/claude/detection_system_v2"
    
    # 1. Find orphan files
    orphans = find_orphan_files(root_dir)
    
    # 2. Find duplicate classes
    duplicates = find_duplicate_classes(root_dir)
    
    # 3. Analyze file sizes
    files_by_size = analyze_file_sizes(root_dir)
    
    # 4. Check model duplications
    check_model_duplications(root_dir)
    
    # 5. Generate refactoring plan
    actions = generate_refactoring_plan(orphans, duplicates)
    
    print("\n" + "=" * 60)
    print("✅ ANALYSE TERMINÉE")
    print("=" * 60)
    print()
