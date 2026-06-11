import argparse
import sys
import json
from pathlib import Path
import hashlib
import zlib
 
class GitObject:
    def __init__(self, obj_type: str, content: bytes):
        self.type = obj_type
        self.content = content
 
    def hash(self) -> str:
        # Git's format: "<type> <size>\0<content>"  → SHA1 of that
        header = f"{self.type} {len(self.content)}\0".encode()
        return hashlib.sha1(header + self.content).hexdigest()
 
    def seralize(self) -> bytes:
        header = f"{self.type} {len(self.content)}\0".encode()
        return zlib.compress(header + self.content)
 
    @classmethod
    def deseralize(cls, data: bytes) -> "GitObject":
        decompressed = zlib.decompress(data)
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx]
        content = decompressed[null_idx + 1:]
        obj_type, size = header.split(b" ")   
        return cls(obj_type.decode(), content)
 
 
class Blob(GitObject):
    def __init__(self, content: bytes):
        super().__init__("blob", content)
 
    def get_content(self) -> bytes:
        return self.content
 
 
class Repository:
    def __init__(self, path="."):
        self.path = Path(path).resolve()
        self.get_dir = self.path / ".bogit"
 
        self.objects_dir = self.get_dir / "objects"   
        self.ref_dir     = self.get_dir / "refs"    
        self.heads_dir   = self.ref_dir / "heads"      
        self.head_file   = self.get_dir / "HEAD"       
        self.index_file  = self.get_dir / "index"      
 
    def init(self) -> bool:
        if self.get_dir.exists():
            return False
 
        self.get_dir.mkdir(parents=True)
        self.objects_dir.mkdir(parents=True)
        self.ref_dir.mkdir(parents=True)
        self.heads_dir.mkdir(parents=True)
 
        self.head_file.write_text("ref: refs/heads/Alpha_Line\n")
        
        self.save_index({})
 
        print("Initialized empty bogit repository in", self.get_dir)
        return True
 
    def store_object(self, obj: GitObject):
        obj_hash = obj.hash()
        obj_dir  = self.objects_dir / obj_hash[:2] 
        obj_file = obj_dir / obj_hash[2:]           
 
        if not obj_file.exists():
            obj_dir.mkdir(exist_ok=True)
            obj_file.write_bytes(obj.seralize())
        return obj_hash
 
    def load_index(self) -> dict[str, str]:
        if not self.index_file.exists():
            return {}
        try:
            return json.loads(self.index_file.read_text())
        except:
            return {}
 
    def save_index(self, index: dict[str, str]):
        self.index_file.write_text(json.dumps(index, indent=2))
 
    def add_file(self, path: str):
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path '{path}' not found")
 
        content   = full_path.read_bytes()   # 1. read raw bytes
        blob      = Blob(content)            # 2. create Blob object
        blob_hash = self.store_object(blob)  # 3. compress + save to .bogit/objects/
 
        index        = self.load_index()     # 4. load current staging area
        index[path]  = blob_hash             # 5. map filepath → hash
        self.save_index(index)               # 6. write it back to disk
 
        print(f"Added '{path}' → {blob_hash[:7]}...")
    
    def add_directory(self , path : str):
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path '{path}' not found")
        if not full_path.is_dir():
            raise ValueError(f"{path} is not a directory")
        #recursivly traverse all directory
        index = self.load_index()
        added_count = 0
        for file_path in full_path.rglob("*"):
            if file_path.is_file():
                if ".bogit" in file_path.parts:
                    continue
               
                #create blob for file
                content = file_path.read_bytes()
                blob = Blob(content)
                blob_hash = self.store_object(blob)  
                #update index 
                rel_path = str(file_path.relative_to(self.path))
                index[rel_path] = blob_hash
                added_count += 1
        self.save_index(index)
        if added_count > 0 :
            print(f"ADded {added_count} files from directory {path}")
        else:
            print("directory part is already updated")
    def add_path(self, path: str) -> None:
        full_path = self.path / path
 
        if not full_path.exists():
            raise FileNotFoundError(f"Path '{path}' not found")
        if full_path.is_file():
            self.add_file(path)
        elif full_path.is_dir():
            self.add_directory(path)
        else:
            raise ValueError(f"'{path}' is neither a file nor a directory")
 
 
def main():
    parser = argparse.ArgumentParser(description="Bogit : THE BAO-GIT")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
 
    init_parser = subparsers.add_parser("init", help="Initialise a new Repository")
 
    add_parser = subparsers.add_parser("add", help="Adds file(s) and Directory to the staging area")
    add_parser.add_argument("paths", nargs='+', help="Files and directories to add")
    
    #commint parser
    commit_parser = subparsers.add_parser("commit" , hepl="create a New Commit ")
    commit_parser.add_argument("-m", "--message" , help="commit message" , required=True)
    commit_parser.add_argument("--author" , hepl="Author name and email")
    args = parser.parse_args()
 
    if not args.command:
        parser.print_help()
        return
 
    try:
        repo = Repository()
        if args.command == "init":
            if not repo.init():
                print("Repository already exists")
                return
 
        elif args.command == "add":
            if not repo.get_dir.exists():
                print("Not a Bogit Repository")
                return
            for path in args.paths:
                repo.add_path(path)
        elif args.command == "commit":
            args.auth
            if not repo.get_dir.exists():
                print("not a Bogit Directory")
                return
            
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
 
 
main()